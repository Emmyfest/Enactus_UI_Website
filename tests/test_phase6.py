import tempfile
from datetime import timedelta
from django.contrib.auth.models import Permission
from django.core.cache import cache
from django.core.exceptions import PermissionDenied
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase,override_settings
from django.utils import timezone
from apps.accounts.models import Role,User
from apps.comms.models import Notification
from apps.core.models import AuditLog,SiteSetting
from apps.documents.models import Document,DocumentVersion
from apps.events.models import Attendance,Event
from apps.members.models import Application,Department,MemberProfile,RecruitmentPeriod
PW='Str0ng-pass-ph4se!'
def mk(e,verified=False,name=None): return User.objects.create_user(e,PW,full_name=name or e.split('@')[0].title(),email_verified=verified)
def grant(u,*codes):
    r=Role.objects.create(name=f'r{u.pk}{codes[0]}',slug=f'r{u.pk}{codes[0]}'); r.permissions.add(*Permission.objects.filter(codename__in=codes)); u.roles.add(r); return r
class RecruitmentJourney(TestCase):
    def setUp(self):
        cache.clear(); n=timezone.now(); self.per=RecruitmentPeriod.objects.create(name='2026 Intake',opens=n-timedelta(days=1),closes=n+timedelta(days=5))
        self.rev=mk('rev@x.org'); grant(self.rev,'review_application')
        self.data={'full_name':'Ada Obi','email':'ada@x.org','motivation':'I want to build things.'}
    def apply(self): self.client.post('/join/',self.data); return Application.objects.get()
    def decide(self,a,**k): self.client.force_login(self.rev); return self.client.post(f'/applications/{a.pk}/decide/',k)
    def check(self,ref,email): return self.client.post('/recruit/status/',{'reference':ref,'email':email})
    def test_landing_open_and_closed(self):
        self.assertContains(self.client.get('/recruit/'),'Applications are open'); RecruitmentPeriod.objects.update(is_active=False); self.assertContains(self.client.get('/recruit/'),'Applications are closed')
    def test_applicant_follows_status_end_to_end(self):
        a=self.apply(); self.assertContains(self.check(a.reference,'ada@x.org'),'Received')
        self.decide(a,decision='shortlisted'); self.assertContains(self.check(a.reference,'ada@x.org'),'Shortlisted')
        self.decide(a,decision='interview',interview_at='2026-12-01T10:00',applicant_message='Zoom link: https://meet.example/abc'); r=self.check(a.reference.lower(),'ADA@x.org')
        self.assertContains(r,'Interview invitation'); self.assertContains(r,'meet.example'); self.assertContains(r,'01 Dec 2026')
        SiteSetting.objects.create(key='onboarding_instructions',value='Join the WhatsApp group.'); self.decide(a,decision='accepted',note='strong candidate'); r=self.check(a.reference,'ada@x.org')
        self.assertContains(r,'been admitted'); self.assertContains(r,'WhatsApp group'); self.assertNotContains(r,'strong candidate')
    def test_rejection_shows_kind_message_not_internal_note(self):
        a=self.apply(); self.decide(a,decision='rejected',note='weak essay',applicant_message='Please apply again next year.'); r=self.check(a.reference,'ada@x.org')
        self.assertContains(r,'Not successful'); self.assertContains(r,'apply again next year'); self.assertNotContains(r,'weak essay')
    def test_status_needs_matching_email_and_does_not_leak(self):
        a=self.apply(); r=self.check(a.reference,'someone@else.org'); self.assertContains(r,'No application matches'); self.assertNotContains(r,'Ada Obi')
    def test_status_lookup_is_rate_limited(self):
        for _ in range(10): self.check('ENA-NOPE','x@x.org')
        self.assertEqual(self.check('ENA-NOPE','x@x.org').status_code,429)
    def test_interview_needs_date_and_message(self):
        a=self.apply(); self.decide(a,decision='interview'); a.refresh_from_db(); self.assertEqual(a.status,'pending')
    def test_non_reviewer_cannot_decide(self):
        a=self.apply(); self.client.force_login(mk('o@x.org')); self.assertEqual(self.client.post(f'/applications/{a.pk}/decide/',{'decision':'accepted'}).status_code,403)
    def test_accepted_applicant_with_verified_account_becomes_probationary(self):
        u=mk('ada@x.org',verified=True); a=self.apply(); self.decide(a,decision='accepted'); self.assertEqual(MemberProfile.objects.get(user=u).status,'probationary'); self.assertTrue(Notification.objects.filter(user=u).exists())
    def test_unverified_account_gets_nothing_until_verified(self):
        u=mk('ada@x.org'); a=self.apply(); self.decide(a,decision='accepted'); self.assertFalse(MemberProfile.objects.exists())
        from django.core import signing
        self.client.get('/accounts/verify/'+signing.dumps(u.pk,salt='verify')+'/'); self.assertEqual(MemberProfile.objects.get(user=u).status,'probationary')
class MemberExport(TestCase):
    def setUp(self):
        d=Department.objects.create(name='Tech'); self.exp=mk('exp@x.org'); grant(self.exp,'export_members','view_memberprofile'); self.sens=mk('sens@x.org'); grant(self.sens,'export_members','view_memberprofile','view_sensitive')
        MemberProfile.objects.create(user=mk('m1@x.org',name='Active One'),status='active',department=d,matric_number='MAT123',phone='0800111'); MemberProfile.objects.create(user=mk('m2@x.org',name='Gone Two'),status='inactive')
        MemberProfile.objects.create(user=mk('m3@x.org',name='=EVIL()'),status='active')
    def test_requires_permission(self):
        self.assertEqual(self.client.get('/members/export.csv').status_code,302); self.client.force_login(mk('plain@x.org')); self.assertEqual(self.client.get('/members/export.csv').status_code,403)
    def test_sensitive_columns_need_extra_permission(self):
        self.client.force_login(self.exp); c=self.client.get('/members/export.csv').content.decode(); self.assertIn('Active One',c); self.assertNotIn('MAT123',c); self.assertNotIn('0800111',c)
        self.client.force_login(self.sens); c=self.client.get('/members/export.csv').content.decode(); self.assertIn('MAT123',c); self.assertIn('0800111',c)
    def test_filters_audit_and_formula_safety(self):
        self.client.force_login(self.exp); c=self.client.get('/members/export.csv?status=active').content.decode(); self.assertNotIn('Gone Two',c); self.assertIn("'=EVIL()",c)
        self.assertTrue(AuditLog.objects.filter(action='members.exported',detail__contains='2 rows').exists())
    def test_list_hides_sensitive_without_permission(self):
        self.client.force_login(self.exp); self.assertNotContains(self.client.get('/members/'),'MAT123'); self.client.force_login(self.sens); self.assertContains(self.client.get('/members/'),'MAT123')
    def test_applications_export_protected(self):
        self.client.force_login(self.exp); self.assertEqual(self.client.get('/applications/export.csv').status_code,403)
class QRCheckin(TestCase):
    def setUp(self):
        self.e=Event.objects.create(title='Ev',slug='ev',starts=timezone.now(),is_published=True); self.st=mk('st@x.org'); grant(self.st,'manage_attendance'); self.u=mk('u@x.org')
    def url(self,t=None): return f'/events/ev/checkin/{t or self.e.checkin_token}/'
    def test_staff_only_qr_image(self):
        self.client.force_login(self.u); self.assertEqual(self.client.get('/events/ev/qr.svg').status_code,403); self.client.force_login(self.st); r=self.client.get('/events/ev/qr.svg'); self.assertEqual((r.status_code,r['Content-Type']),(200,'image/svg+xml'))
    def test_closed_by_default(self):
        self.client.force_login(self.u); self.client.post(self.url()); self.assertEqual(Attendance.objects.count(),0)
    def test_scan_requires_confirmation_and_records_once(self):
        Event.objects.update(checkin_open=True); self.client.force_login(self.u); self.client.get(self.url()); self.assertEqual(Attendance.objects.count(),0)
        for _ in range(2): self.client.post(self.url())
        a=Attendance.objects.get(); self.assertEqual((a.user,a.method),(self.u,'qr'))
    def test_login_required_and_wrong_token(self):
        Event.objects.update(checkin_open=True); self.assertEqual(self.client.get(self.url()).status_code,302); self.client.force_login(self.u); self.assertEqual(self.client.post(self.url('wrong')).status_code,404)
    def test_regenerate_invalidates_old_code_and_open_close_audited(self):
        self.client.force_login(self.st); old=self.e.checkin_token; self.client.post('/events/ev/checkin/control/',{'action':'open'}); self.client.post('/events/ev/checkin/control/',{'action':'regenerate'}); self.e.refresh_from_db()
        self.assertNotEqual(old,self.e.checkin_token); self.assertTrue(self.e.checkin_open); self.client.force_login(self.u); self.assertEqual(self.client.post(self.url(old)).status_code,404); self.assertTrue(AuditLog.objects.filter(action='checkin.open').exists())
    def test_control_needs_permission(self):
        self.client.force_login(self.u); self.assertEqual(self.client.post('/events/ev/checkin/control/',{'action':'open'}).status_code,403)
class Documents(TestCase):
    def setUp(self):
        self.tmp=tempfile.mkdtemp(); o=override_settings(PRIVATE_MEDIA_ROOT=self.tmp); o.enable(); self.addCleanup(o.disable)
        self.sec=mk('sec@x.org'); grant(self.sec,'add_document','change_document'); self.mem=mk('mem@x.org'); self.role_user=mk('ru@x.org'); self.role=grant(self.role_user,'view_document')
    def up(self,title='Doc',access='members',name='a.pdf',body=b'%PDF-1',**k):
        self.client.force_login(self.sec); return self.client.post('/documents/upload/',{'title':title,'category':'policy','access':access,'file':SimpleUploadedFile(name,body),**k})
    def test_upload_creates_v1_with_checksum_and_audit(self):
        self.up(); d=Document.objects.get(); v=d.latest; self.assertEqual((v.number,len(v.sha256),d.owner),(1,64,self.sec)); self.assertTrue(AuditLog.objects.filter(action='document.uploaded').exists())
    def test_only_permitted_users_upload(self):
        self.client.force_login(self.mem); self.assertEqual(self.client.post('/documents/upload/',{'title':'x'}).status_code,403)
    def test_file_type_and_size_rules(self):
        self.up(name='evil.exe',body=b'MZ'); self.assertEqual(Document.objects.count(),0); self.up(name='big.pdf',body=b'0'*(10*1024*1024+1)); self.assertEqual(Document.objects.count(),0)
    def test_new_version_keeps_history_and_old_download_works(self):
        self.up(body=b'one'); d=Document.objects.get(); self.client.post(f'/documents/{d.pk}/version/',{'file':SimpleUploadedFile('a.pdf',b'two'),'note':'fix'}); self.assertEqual(d.versions.count(),2)
        self.assertEqual(b''.join(self.client.get(f'/documents/{d.pk}/download/').streaming_content),b'two'); self.assertEqual(b''.join(self.client.get(f'/documents/{d.pk}/download/1/').streaming_content),b'one')
    def test_non_manager_cannot_add_version(self):
        self.up(); d=Document.objects.get(); self.client.force_login(self.mem); self.assertEqual(self.client.post(f'/documents/{d.pk}/version/',{'file':SimpleUploadedFile('a.pdf',b'x')}).status_code,404)
    def test_access_levels(self):
        self.up('Pub','public'); self.up('Mem','members'); self.up('Priv','private'); self.up('Rol','roles',roles=[self.role.pk]); self.client.logout(); ids={d.title:d.pk for d in Document.objects.all()}
        c=self.client.get('/documents/').content.decode(); self.assertIn('Pub',c); self.assertNotIn('>Mem<',c)
        self.assertEqual(self.client.get(f"/documents/{ids['Pub']}/download/").status_code,200); 
        for t in('Mem','Priv','Rol'): self.assertEqual(self.client.get(f'/documents/{ids[t]}/download/').status_code,404)
        self.client.force_login(self.mem); self.assertEqual(self.client.get(f"/documents/{ids['Mem']}/download/").status_code,200)
        for t in('Priv','Rol'): self.assertEqual(self.client.get(f'/documents/{ids[t]}/download/').status_code,404)
        self.client.force_login(self.role_user); self.assertEqual(self.client.get(f"/documents/{ids['Rol']}/download/").status_code,200); self.assertEqual(self.client.get(f"/documents/{ids['Priv']}/download/").status_code,404)
        self.client.force_login(self.sec); self.assertEqual(self.client.get(f"/documents/{ids['Priv']}/download/").status_code,200)
    def test_restricted_downloads_audited_public_not(self):
        self.up('Pub','public'); self.up('Mem','members'); self.client.logout(); ids={d.title:d.pk for d in Document.objects.all()}; self.client.get(f"/documents/{ids['Pub']}/download/"); self.assertFalse(AuditLog.objects.filter(action='document.downloaded').exists())
        self.client.force_login(self.mem); self.client.get(f"/documents/{ids['Mem']}/download/"); self.assertTrue(AuditLog.objects.filter(action='document.downloaded').exists())
    def test_archive_hides_but_never_deletes(self):
        self.up(); d=Document.objects.get(); self.client.post(f'/documents/{d.pk}/archive/'); self.assertNotContains(self.client.get('/documents/'),'Doc</a>'); self.assertRaises(PermissionDenied,d.delete); self.assertEqual(DocumentVersion.objects.count(),1)
    def test_versions_immutable_and_not_publicly_urlable(self):
        self.up(); v=DocumentVersion.objects.get(); v.note='x'; self.assertRaises(PermissionDenied,v.save); self.assertRaises(PermissionDenied,v.delete); self.assertRaises(ValueError,lambda:v.file.url)
    def test_filter_by_administration_and_search(self):
        from apps.executives.models import Administration
        ad=Administration.objects.create(title='2025/26',start='2025-09-01'); self.up('Annual',administration=ad.pk); self.up('Zebra')
        c=self.client.get(f'/documents/?administration={ad.pk}').content.decode(); self.assertIn('Annual',c); self.assertNotIn('Zebra',c); self.assertIn('Zebra',self.client.get('/documents/?q=zeb').content.decode())
