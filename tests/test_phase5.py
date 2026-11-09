import tempfile
from datetime import date,timedelta
from decimal import Decimal
from io import BytesIO
from django.contrib.auth.models import Permission
from django.core.exceptions import PermissionDenied
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase,override_settings
from django.utils import timezone
from PIL import Image
from apps.accounts.models import Role,User
from apps.comms.models import Notification
from apps.core.models import AuditLog,MediaAsset
from apps.events.models import Event,Registration
from apps.finance.models import FinancialEntry
from apps.impact.models import ImpactRecord
from apps.members.models import Application,MemberProfile,RecruitmentPeriod
from apps.network.models import AlumniProfile,FacultyAssignment,FacultyProfile
from apps.projects.models import Project,ProjectMember,Task
PW='Str0ng-pass-ph4se!'
def mk(e): return User.objects.create_user(e,PW,full_name=e.split('@')[0].title())
def grant(u,*codes):
    r=Role.objects.create(name=f'r{u.pk}{codes[0]}',slug=f'r{u.pk}{codes[0]}'); r.permissions.add(*Permission.objects.filter(codename__in=codes)); u.roles.add(r)
def png(name='a.png'):
    b=BytesIO(); Image.new('RGB',(8,8),'orange').save(b,'PNG'); return SimpleUploadedFile(name,b.getvalue(),content_type='image/png')
class FinanceTests(TestCase):
    def setUp(self):
        self.rec,self.app,self.out=mk('rec@x.org'),mk('app@x.org'),mk('out@x.org'); grant(self.rec,'record_finance','view_finance'); grant(self.app,'approve_finance','view_finance')
        self.p=Project.objects.create(name='P',slug='p')
    def entry(self,kind='expense',amount='100',status='draft',**k): return FinancialEntry.objects.create(project=self.p,kind=kind,description=k.pop('description','item'),amount=Decimal(amount),date=date.today(),created_by=self.rec,status=status,**k)
    def test_restricted_to_permission_holders(self):
        for u in (None,self.out):
            if u: self.client.force_login(u)
            self.assertIn(self.client.get('/finance/').status_code,(302,403))
        self.client.force_login(self.rec); self.assertEqual(self.client.get('/finance/').status_code,200)
    def test_only_recorders_create(self):
        self.client.force_login(self.app); self.assertEqual(self.client.get('/finance/new/').status_code,403)
        self.client.force_login(self.rec); self.client.post('/finance/new/',{'kind':'budget','description':'Seed','amount':'500','date':'2026-01-01','project':self.p.pk}); self.assertEqual(FinancialEntry.objects.get().created_by,self.rec)
    def test_negative_amount_rejected(self):
        self.client.force_login(self.rec); self.client.post('/finance/new/',{'kind':'budget','description':'x','amount':'-5','date':'2026-01-01'}); self.assertEqual(FinancialEntry.objects.count(),0)
    def test_creator_cannot_approve_and_approver_can(self):
        e=self.entry(status='submitted'); grant(self.rec,'approve_finance'); self.client.force_login(self.rec); self.assertEqual(self.client.post(f'/finance/{e.pk}/action/',{'action':'approved'}).status_code,403)
        self.client.force_login(self.app); self.client.post(f'/finance/{e.pk}/action/',{'action':'approved'}); e.refresh_from_db(); self.assertEqual((e.status,e.approved_by),('approved',self.app))
        self.assertTrue(AuditLog.objects.filter(action='finance.approved').exists()); self.assertTrue(Notification.objects.filter(user=self.rec).exists())
    def test_recorder_cannot_approve_without_permission(self):
        e=self.entry(status='submitted'); mid=mk('mid@x.org'); grant(mid,'record_finance','view_finance'); self.client.force_login(mid); self.assertEqual(self.client.post(f'/finance/{e.pk}/action/',{'action':'approved'}).status_code,403)
    def test_approved_entry_locked(self):
        e=self.entry(status='approved'); e.amount=Decimal('1'); self.assertRaises(PermissionDenied,e.save); self.assertRaises(PermissionDenied,e.delete)
        self.client.force_login(self.rec); self.assertEqual(self.client.post(f'/finance/{e.pk}/edit/',{'kind':'expense','description':'x','amount':'1','date':'2026-01-01'}).status_code,403)
    def test_totals_use_approved_only_and_kinds_stay_separate(self):
        self.entry('budget','1000',status='approved'); self.entry('expense','300',status='approved'); self.entry('income','50',status='approved'); self.entry('commitment','70',status='approved'); self.entry('expense','9999',status='submitted',description='PendingSpend')
        self.client.force_login(self.rec); c=self.client.get('/finance/').content.decode(); self.assertIn('700.00',c); self.assertNotIn('10299',c); self.assertNotIn('9999',c.split('Recent entries')[0])
    def test_voiding_removes_entry_from_totals_without_overwriting(self):
        bad=self.entry('expense','300',status='approved'); self.entry('expense','0',status='approved',voids=bad,description='void'); ok=self.entry('expense','40',status='approved')
        self.client.force_login(self.rec); c=self.client.get('/finance/').content.decode(); self.assertNotIn('340.00',c); self.assertIn('40.00',c); bad.refresh_from_db(); self.assertEqual(bad.amount,Decimal('300'))
    def test_void_needs_zero_amount_and_receipt_type_checked(self):
        bad=self.entry(status='approved'); self.client.force_login(self.rec); self.client.post('/finance/new/',{'kind':'expense','description':'v','amount':'5','date':'2026-01-01','voids':bad.pk}); self.assertEqual(FinancialEntry.objects.count(),1)
        with override_settings(MEDIA_ROOT=tempfile.mkdtemp()):
            self.client.post('/finance/new/',{'kind':'expense','description':'r','amount':'5','date':'2026-01-01','receipt':SimpleUploadedFile('r.exe',b'MZ')}); self.assertEqual(FinancialEntry.objects.count(),1)
class NetworkTests(TestCase):
    DATA={'graduation_year':'2022','department':'Agric Eng','previous_positions':'Project Manager','skills':'Python, IoT','employer':'Acme','industry':'Tech'}
    def test_profile_hidden_until_approved_and_public(self):
        u=mk('al@x.org'); self.client.force_login(u); self.client.post('/alumni/me/',{**self.DATA,'public_profile':'on'}); self.client.logout()
        self.assertNotContains(self.client.get('/alumni/'),'Project Manager'); AlumniProfile.objects.update(is_approved=True); self.assertContains(self.client.get('/alumni/'),'Project Manager')
    def test_private_by_default_and_field_switches(self):
        u=mk('al@x.org'); self.client.force_login(u); self.client.post('/alumni/me/',self.DATA); AlumniProfile.objects.update(is_approved=True); self.client.logout()
        self.assertNotContains(self.client.get('/alumni/'),'Project Manager')
        AlumniProfile.objects.update(public_profile=True); c=self.client.get('/alumni/'); self.assertContains(c,'Project Manager'); self.assertNotContains(c,'Acme'); self.assertNotContains(c,'IoT'); self.assertNotContains(c,'al@x.org')
        AlumniProfile.objects.update(show_employer=True,show_skills=True,show_email=True); c=self.client.get('/alumni/'); self.assertContains(c,'Acme'); self.assertContains(c,'IoT'); self.assertContains(c,'al@x.org')
    def test_editing_requires_reapproval(self):
        u=mk('al@x.org'); AlumniProfile.objects.create(user=u,is_approved=True,public_profile=True); self.client.force_login(u); self.client.post('/alumni/me/',{**self.DATA,'public_profile':'on'}); self.assertFalse(AlumniProfile.objects.get().is_approved)
    def test_mentors_need_login_and_approval(self):
        u=mk('al@x.org'); AlumniProfile.objects.create(user=u,mentorship_available=True,skills='Mentoring-skill'); self.assertEqual(self.client.get('/alumni/mentors/').status_code,302)
        self.client.force_login(mk('m@x.org')); self.assertNotContains(self.client.get('/alumni/mentors/'),'Mentoring-skill'); AlumniProfile.objects.update(is_approved=True); self.assertContains(self.client.get('/alumni/mentors/'),'Mentoring-skill')
    def test_advisors_public_only_when_approved(self):
        f=mk('zelda@x.org'); FacultyProfile.objects.create(user=f,title='Dr',is_public=True); self.assertNotContains(self.client.get('/advisors/'),'Zelda'); FacultyProfile.objects.update(is_approved=True); self.assertContains(self.client.get('/advisors/'),'Zelda')
    def test_faculty_portal_restricted(self):
        self.client.force_login(mk('x@x.org')); self.assertEqual(self.client.get('/faculty/').status_code,403)
class FacultyScopeTests(TestCase):
    def test_assigned_advisor_reviews_only_assigned_projects(self):
        fa,rep=mk('fa@x.org'),mk('rep@x.org'); grant(fa,'verify_impact','review_report'); FacultyProfile.objects.create(user=fa,is_approved=True)
        a,b=Project.objects.create(name='A',slug='a',is_public=True),Project.objects.create(name='B',slug='b',is_public=True); FacultyAssignment.objects.create(user=fa,project=a)
        mkr=lambda p:ImpactRecord.objects.create(project=p,indicator='I',category='direct',period_start=date(2026,1,1),period_end=date(2026,2,1),actual=1,unit='u',method='m',reporting_officer=rep,status='submitted')
        ra,rb=mkr(a),mkr(b); self.client.force_login(fa)
        self.assertEqual(self.client.post(f'/impact/records/{ra.pk}/action/',{'action':'approved'}).status_code,302); ra.refresh_from_db(); self.assertEqual(ra.status,'approved')
        self.assertEqual(self.client.post(f'/impact/records/{rb.pk}/action/',{'action':'approved'}).status_code,403); self.assertEqual(self.client.get(f'/impact/records/{rb.pk}/').status_code,404)
        self.assertNotContains(self.client.get('/impact/review/'),'/impact/records/%d/'%rb.pk)
class DashboardTests(TestCase):
    def test_member_sees_only_own_data(self):
        a,b=mk('a@x.org'),mk('b@x.org'); p=Project.objects.create(name='Mine',slug='m'); q=Project.objects.create(name='Theirs',slug='t'); ProjectMember.objects.create(project=p,user=a); ProjectMember.objects.create(project=q,user=b)
        Task.objects.create(project=p,title='MyTask',assignee=a); Task.objects.create(project=q,title='OtherTask',assignee=b); self.client.force_login(a); c=self.client.get('/dashboard/').content.decode()
        self.assertIn('Mine',c); self.assertIn('MyTask',c); self.assertNotIn('Theirs',c); self.assertNotIn('OtherTask',c)
    def test_no_fabricated_numbers_on_empty_system(self):
        u=mk('a@x.org'); self.client.force_login(u); c=self.client.get('/dashboard/').content.decode(); self.assertIn('not on a project team',c); self.assertNotIn('Executive overview',c); self.assertNotIn('Platform',c)
    def test_sections_follow_roles(self):
        u=mk('ex@x.org'); grant(u,'review_application'); self.client.force_login(u); self.assertContains(self.client.get('/dashboard/'),'Executive overview'); self.assertNotContains(self.client.get('/dashboard/'),'Pending approvals')
    def test_executive_figures_come_from_database(self):
        u=mk('ex@x.org'); grant(u,'review_application'); n=timezone.now(); per=RecruitmentPeriod.objects.create(name='P',opens=n,closes=n+timedelta(days=1))
        for i in range(3): Application.objects.create(period=per,full_name=f'A{i}',email=f'a{i}@x.org',motivation='m')
        MemberProfile.objects.create(user=mk('m@x.org'),status='active'); self.client.force_login(u); c=self.client.get('/dashboard/').content.decode(); self.assertIn('Pending applications: <strong>3</strong>',c); self.assertIn('Active: 1',c)
    def test_superuser_sees_platform_and_pending(self):
        s=User.objects.create_superuser('root@x.org',PW,full_name='Root'); FinancialEntry.objects.create(kind='budget',description='d',amount=1,date=date.today(),created_by=s,status='submitted'); self.client.force_login(s)
        c=self.client.get('/dashboard/').content.decode(); self.assertIn('Pending approvals',c); self.assertIn('Financial entries: <strong>1</strong>',c); self.assertIn('reachable',c)
    def test_alumni_and_faculty_sections(self):
        u=mk('al@x.org'); AlumniProfile.objects.create(user=u); FacultyProfile.objects.create(user=u); self.client.force_login(u); c=self.client.get('/dashboard/').content.decode(); self.assertIn('Alumni',c); self.assertIn('Faculty advisor',c)
class MediaTests(TestCase):
    def setUp(self):
        self.tmp=tempfile.mkdtemp(); self.o=override_settings(MEDIA_ROOT=self.tmp); self.o.enable(); self.addCleanup(self.o.disable)
        self.admin,self.out=mk('wa@x.org'),mk('out@x.org'); grant(self.admin,'manage_media')
    def up(self,**k): return self.client.post('/library/',{'file':png(),'title':'Team','alt_text':'The team','category':'team',**k})
    def test_permission_required(self):
        self.assertEqual(self.client.get('/library/').status_code,302); self.client.force_login(self.out); self.assertEqual(self.client.get('/library/').status_code,403); self.assertEqual(self.up().status_code,403)
    def test_upload_validation(self):
        self.client.force_login(self.admin); self.up(); self.assertEqual(MediaAsset.objects.count(),1)
        self.client.post('/library/',{'file':SimpleUploadedFile('x.png',b'not an image'),'title':'t','alt_text':'a','category':'team'}); self.assertEqual(MediaAsset.objects.count(),1)
        self.client.post('/library/',{'file':SimpleUploadedFile('x.svg',b'<svg/>'),'title':'t','alt_text':'a','category':'team'}); self.assertEqual(MediaAsset.objects.count(),1)
        self.client.post('/library/',{'file':png(),'title':'t','category':'team'}); self.assertEqual(MediaAsset.objects.count(),1)
    def test_private_by_default_public_gallery_and_featured(self):
        self.client.force_login(self.admin); self.up(); self.client.logout(); self.assertNotContains(self.client.get('/gallery/'),'The team')
        MediaAsset.objects.update(is_public=True); self.assertContains(self.client.get('/gallery/'),'The team'); self.assertNotContains(self.client.get('/'),'The team'); MediaAsset.objects.update(is_featured=True); self.assertContains(self.client.get('/'),'The team')
    def test_toggle_replace_delete_with_confirmation(self):
        self.client.force_login(self.admin); self.up(); a=MediaAsset.objects.get(); old=a.file.path
        self.client.post(f'/library/{a.pk}/toggle/',{'field':'is_featured'}); a.refresh_from_db(); self.assertTrue(a.is_featured)
        self.client.post(f'/library/{a.pk}/replace/',{'file':png('b.png')}); a.refresh_from_db(); self.assertNotEqual(a.file.path,old)
        import os; self.assertFalse(os.path.exists(old))
        self.client.post(f'/library/{a.pk}/delete/',{}); self.assertEqual(MediaAsset.objects.count(),1)
        self.client.post(f'/library/{a.pk}/delete/',{'confirm':'yes'}); self.assertEqual(MediaAsset.objects.count(),0); self.assertTrue(AuditLog.objects.filter(action='media.deleted').exists())
