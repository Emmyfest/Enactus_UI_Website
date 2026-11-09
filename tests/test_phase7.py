import tempfile
from datetime import date,timedelta
from django.contrib.auth.models import Permission
from django.core import mail
from django.core.cache import cache
from django.core.exceptions import PermissionDenied
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.test import TestCase,override_settings
from django.utils import timezone
from apps.academy.models import Course,CourseResource,Enrolment
from apps.accounts.models import Role,User
from apps.comms.models import Notification
from apps.core.models import AuditLog
from apps.documents.models import Document
from apps.events.models import Event
from apps.executives.models import Administration,HandoverItem,HandoverPack
from apps.opportunities.models import Opportunity
from apps.partnerships.models import Enquiry,Partner
from apps.projects.models import Project,ProjectMember,Task,TaskAttachment
PW='Str0ng-pass-ph4se!'
def mk(e,name=None): return User.objects.create_user(e,PW,full_name=name or e.split('@')[0].title())
def grant(u,*codes):
    r=Role.objects.create(name=f'r{u.pk}{codes[0]}',slug=f'r{u.pk}{codes[0]}'); r.permissions.add(*Permission.objects.filter(codename__in=codes)); u.roles.add(r)
class AcademyTests(TestCase):
    def setUp(self):
        self.tr,self.mem,self.out=mk('tr@x.org'),mk('mem@x.org'),mk('out@x.org'); self.c=Course.objects.create(title='Pitching 101',slug='pitch',trainer=self.tr,is_published=True)
        self.r1=CourseResource.objects.create(course=self.c,title='Slides',url='https://example.org/s',order=1); self.r2=CourseResource.objects.create(course=self.c,title='Task',kind='assignment',instructions='Do it',order=2)
    def test_unpublished_hidden_and_links_locked_until_enrolled(self):
        Course.objects.create(title='Secret',slug='sec'); self.assertNotContains(self.client.get('/academy/'),'Secret'); self.assertEqual(self.client.get('/academy/sec/').status_code,404)
        self.assertNotContains(self.client.get('/academy/pitch/'),'https://example.org/s'); self.client.force_login(self.mem); self.client.post('/academy/pitch/enrol/'); self.assertContains(self.client.get('/academy/pitch/'),'https://example.org/s')
    def test_enrol_once_and_progress(self):
        self.client.force_login(self.mem)
        for _ in range(2): self.client.post('/academy/pitch/enrol/')
        self.assertEqual(Enrolment.objects.count(),1); self.client.post(f'/academy/pitch/resources/{self.r1.pk}/done/'); self.client.post(f'/academy/pitch/resources/{self.r1.pk}/done/'); self.assertEqual(Enrolment.objects.get().progress_pct,50)
    def test_cannot_mark_without_enrolment(self):
        self.client.force_login(self.out); self.assertEqual(self.client.post(f'/academy/pitch/resources/{self.r1.pk}/done/').status_code,403)
    def test_only_trainer_or_manager_records_results(self):
        e=Enrolment.objects.create(course=self.c,user=self.mem); self.client.force_login(self.out); self.assertEqual(self.client.post(f'/academy/record/{e.pk}/',{'action':'complete'}).status_code,403)
        self.client.force_login(self.tr); self.client.post(f'/academy/record/{e.pk}/',{'action':'complete','score':'88'}); e.refresh_from_db(); self.assertEqual((e.status,str(e.score)),('completed','88.00'))
    def test_bad_score_rejected(self):
        e=Enrolment.objects.create(course=self.c,user=self.mem); self.client.force_login(self.tr); self.client.post(f'/academy/record/{e.pk}/',{'action':'complete','score':'150'}); e.refresh_from_db(); self.assertEqual(e.status,'enrolled')
    def test_certificate_needs_permission_completion_and_is_verifiable(self):
        e=Enrolment.objects.create(course=self.c,user=self.mem); self.client.force_login(self.tr); self.assertEqual(self.client.post(f'/academy/record/{e.pk}/',{'action':'certificate'}).status_code,403)
        grant(self.tr,'issue_certificate'); self.client.post(f'/academy/record/{e.pk}/',{'action':'certificate'}); e.refresh_from_db(); self.assertEqual(e.certificate_code,'')
        e.status='completed'; e.save(); self.client.post(f'/academy/record/{e.pk}/',{'action':'certificate'}); e.refresh_from_db(); self.assertEqual(len(e.certificate_code),12)
        self.client.logout(); r=self.client.get(f'/academy/certificate/{e.certificate_code.lower()}/'); self.assertContains(r,'Mem'); self.assertEqual(self.client.get('/academy/certificate/NOPE/').status_code,404)
        self.assertTrue(Notification.objects.filter(user=self.mem,message__contains='certificate').exists())
class OpportunityTests(TestCase):
    def test_expired_never_shown_as_open(self):
        Opportunity.objects.create(name='Old grant',organiser='X',category='grant',deadline=date.today()-timedelta(days=2),is_published=True,application_url='https://apply.example/old')
        Opportunity.objects.create(name='Fresh grant',organiser='X',category='grant',deadline=date.today()+timedelta(days=9),is_published=True,application_url='https://apply.example/new')
        r=self.client.get('/opportunities/'); c=r.content.decode(); self.assertLess(c.index('Fresh grant'),c.index('Old grant')); self.assertIn('Deadline passed',c)
        o=Opportunity.objects.get(name='Old grant'); d=self.client.get(f'/opportunities/{o.pk}/'); self.assertContains(d,'Applications are closed'); self.assertNotContains(d,'apply.example/old')
    def test_unpublished_hidden(self):
        o=Opportunity.objects.create(name='Draft',organiser='X',category='grant',is_published=False); self.assertEqual(self.client.get(f'/opportunities/{o.pk}/').status_code,404); self.assertNotContains(self.client.get('/opportunities/'),'Draft')
    def test_deadline_reminders_once_per_day(self):
        u=mk('off@x.org'); Opportunity.objects.create(name='Soon',organiser='X',category='grant',deadline=date.today()+timedelta(days=3),is_published=True,monitoring_officer=u)
        call_command('notify_deadlines'); call_command('notify_deadlines'); self.assertEqual(Notification.objects.filter(user=u,message__startswith='Deadline reminder').count(),1)
class PartnershipTests(TestCase):
    def setUp(self): cache.clear()
    def test_public_enquiry_creates_record_and_notifies_staff(self):
        st=mk('st@x.org'); grant(st,'manage_partnerships'); r=self.client.post('/contact/',{'kind':'partnership','name':'Ngozi','email':'n@corp.com','message':'Let us collaborate'}); self.assertEqual(r.status_code,200)
        self.assertEqual(Enquiry.objects.get().kind,'partnership'); self.assertTrue(Notification.objects.filter(user=st).exists())
    def test_honeypot_and_rate_limit(self):
        self.client.post('/contact/',{'kind':'general','name':'Bot','email':'b@x.com','message':'spam','website':'http://spam'}); self.assertEqual(Enquiry.objects.count(),0)
        for i in range(5): self.client.post('/contact/',{'kind':'general','name':'A','email':'a@x.com','message':f'm{i}'})
        self.assertEqual(self.client.post('/contact/',{'kind':'general','name':'A','email':'a@x.com','message':'6th'}).status_code,429)
    def test_staff_only_inbox_and_crm(self):
        Enquiry.objects.create(name='Z',email='z@x.com',message='hi'); self.client.force_login(mk('plain@x.org'))
        for u in('/partnerships/enquiries/','/partnerships/crm/'): self.assertEqual(self.client.get(u).status_code,403)
        st=mk('st@x.org'); grant(st,'manage_partnerships'); self.client.force_login(st); self.assertContains(self.client.get('/partnerships/enquiries/'),'z@x.com')
        e=Enquiry.objects.get(); self.client.post(f'/partnerships/enquiries/{e.pk}/handled/'); e.refresh_from_db(); self.assertEqual((e.status,e.handled_by),('handled',st))
    def test_public_showcase_hides_private_contacts_and_expired(self):
        Partner.objects.create(name='GoodCo',status='active',is_public=True,contact_email='secret@goodco.com',contact_phone='0800999'); Partner.objects.create(name='OldCo',status='active',is_public=True,expires=date.today()-timedelta(days=1)); Partner.objects.create(name='HiddenCo',status='active',is_public=False)
        c=self.client.get('/partners/').content.decode(); self.assertIn('GoodCo',c); self.assertNotIn('OldCo',c); self.assertNotIn('HiddenCo',c); self.assertNotIn('secret@goodco.com',c); self.assertNotIn('0800999',c)
    def test_crm_shows_private_contacts_to_staff_and_logs_interactions(self):
        p=Partner.objects.create(name='Co',contact_email='secret@co.com'); st=mk('st@x.org'); grant(st,'manage_partnerships'); self.client.force_login(st)
        self.client.post(f'/partnerships/crm/{p.pk}/',{'summary':'Met the CEO'}); self.assertContains(self.client.get(f'/partnerships/crm/{p.pk}/'),'secret@co.com'); self.assertContains(self.client.get(f'/partnerships/crm/{p.pk}/'),'Met the CEO')
class HandoverTests(TestCase):
    def setUp(self):
        self.prep,self.acc,self.out=mk('prep@x.org'),mk('acc@x.org'),mk('out@x.org'); grant(self.prep,'prepare_handover','manage_transition'); grant(self.acc,'accept_handover'); self.adm=Administration.objects.create(title='2025/26',start='2025-09-01',is_current=True)
    def make(self): self.client.force_login(self.prep); self.client.post('/leadership/handover/new/'); return HandoverPack.objects.get()
    def test_pack_created_once_with_live_summary(self):
        p=self.make(); self.client.post('/leadership/handover/new/'); self.assertEqual(HandoverPack.objects.count(),1); self.assertIn('Open tasks',p.items.get(section='summary').content)
    def test_permissions(self):
        self.client.force_login(self.out); self.assertEqual(self.client.get('/leadership/handover/').status_code,403); self.assertEqual(self.client.post('/leadership/handover/new/').status_code,403)
    def test_add_items_then_submit_then_other_person_accepts(self):
        p=self.make(); self.client.post(f'/leadership/handover/{p.pk}/',{'section':'finance','title':'Budget notes','content':'All reconciled'}); self.assertEqual(p.items.count(),2)
        self.client.post(f'/leadership/handover/{p.pk}/submit/'); p.refresh_from_db(); self.assertEqual(p.status,'submitted'); self.assertTrue(Notification.objects.filter(user=self.acc).exists())
        grant(self.prep,'accept_handover'); self.assertEqual(self.client.post(f'/leadership/handover/{p.pk}/accept/').status_code,403)
        self.client.force_login(self.acc); self.client.post(f'/leadership/handover/{p.pk}/accept/'); p.refresh_from_db(); self.assertEqual((p.status,p.accepted_by),('accepted',self.acc))
    def test_submitted_and_accepted_packs_are_locked(self):
        p=self.make(); HandoverPack.objects.filter(pk=p.pk).update(status='accepted'); p.refresh_from_db(); p.recommendations='changed'; self.assertRaises(PermissionDenied,p.save)
        self.assertRaises(PermissionDenied,HandoverItem(pack=p,title='x').save); self.client.force_login(self.prep); self.assertEqual(self.client.post(f'/leadership/handover/{p.pk}/',{'title':'late','section':'other'}).status_code,403)
    def test_transition_requires_accepted_handover_and_keeps_history(self):
        self.client.force_login(self.prep); self.client.post('/leadership/transition/',{'title':'2026/27','start':'2026-09-01'}); self.assertEqual(Administration.objects.count(),1); self.assertTrue(Administration.objects.get().is_current)
        p=self.make(); HandoverPack.objects.filter(pk=p.pk).update(status='accepted'); self.client.post('/leadership/transition/',{'title':'2026/27','start':'2026-09-01'})
        old=Administration.objects.get(title='2025/26'); new=Administration.objects.get(title='2026/27'); self.assertEqual((old.is_current,old.archived,str(old.end)),(False,True,'2026-08-31')); self.assertTrue(new.is_current); self.assertTrue(AuditLog.objects.filter(action='administration.transition').exists())
    def test_transition_needs_permission(self):
        self.client.force_login(self.out); self.assertEqual(self.client.get('/leadership/transition/').status_code,403)
class SearchTests(TestCase):
    def test_short_query_and_empty(self):
        self.assertContains(self.client.get('/search/?q=a'),'at least 2'); self.assertContains(self.client.get('/search/?q=zzzz'),'No results')
    def test_results_respect_visibility(self):
        tmp=tempfile.mkdtemp()
        with override_settings(PRIVATE_MEDIA_ROOT=tmp):
            owner=mk('o@x.org'); Project.objects.create(name='Zebra Public',slug='zp',is_public=True); Project.objects.create(name='Zebra Private',slug='zpr')
            Event.objects.create(title='Zebra Gala',slug='zg',starts=timezone.now(),is_published=True); Event.objects.create(title='Zebra Secret Event',slug='zs',starts=timezone.now())
            Opportunity.objects.create(name='Zebra Grant',organiser='x',category='grant',is_published=True); Opportunity.objects.create(name='Zebra Draft Grant',organiser='x',category='grant')
            for t,a in(('Zebra Public Doc','public'),('Zebra Members Doc','members'),('Zebra Private Doc','private')):
                d=Document.objects.create(title=t,access=a,owner=owner)
            Partner.objects.create(name='Zebra Partner',status='active',is_public=True); Partner.objects.create(name='Zebra Hidden Partner')
            c=self.client.get('/search/?q=zebra').content.decode()
            for ok in('Zebra Public<','Zebra Gala','Zebra Grant','Zebra Public Doc','Zebra Partner'): self.assertIn(ok,c)
            for no in('Zebra Private<','Zebra Secret Event','Zebra Draft Grant','Zebra Members Doc','Zebra Private Doc','Zebra Hidden Partner'): self.assertNotIn(no,c)
            m=mk('m@x.org'); self.client.force_login(m); c=self.client.get('/search/?q=zebra').content.decode(); self.assertIn('Zebra Members Doc',c); self.assertNotIn('Zebra Private Doc',c)
    def test_members_only_for_permitted(self):
        from apps.members.models import MemberProfile
        MemberProfile.objects.create(user=mk('findme@x.org',name='Findable Person')); self.assertNotContains(self.client.get('/search/?q=findable'),'Findable Person')
        u=mk('rev@x.org'); grant(u,'view_memberprofile'); self.client.force_login(u); self.assertContains(self.client.get('/search/?q=findable'),'Findable Person')
class TaskCollabTests(TestCase):
    def setUp(self):
        self.tmp=tempfile.mkdtemp(); o=override_settings(PRIVATE_MEDIA_ROOT=self.tmp); o.enable(); self.addCleanup(o.disable)
        self.mgr,self.mem,self.out=mk('mgr@x.org'),mk('mem@x.org'),mk('out@x.org'); self.p=Project.objects.create(name='P',slug='p',manager=self.mgr); ProjectMember.objects.create(project=self.p,user=self.mem); self.t=Task.objects.create(project=self.p,title='Build',assignee=self.mem)
    def test_only_team_can_open_task(self):
        self.client.force_login(self.out); self.assertEqual(self.client.get(f'/tasks/{self.t.pk}/').status_code,404); self.client.force_login(self.mem); self.assertEqual(self.client.get(f'/tasks/{self.t.pk}/').status_code,200)
    def test_comments_notify_others_not_author(self):
        self.client.force_login(self.mem); self.client.post(f'/tasks/{self.t.pk}/comment/',{'body':'Started'}); self.assertEqual(self.t.comments.count(),1); self.assertTrue(Notification.objects.filter(user=self.mgr).exists()); self.assertFalse(Notification.objects.filter(user=self.mem).exists())
    def test_outsider_cannot_comment_and_empty_ignored(self):
        self.client.force_login(self.out); self.assertEqual(self.client.post(f'/tasks/{self.t.pk}/comment/',{'body':'x'}).status_code,404); self.client.force_login(self.mem); self.client.post(f'/tasks/{self.t.pk}/comment/',{'body':'   '}); self.assertEqual(self.t.comments.count(),0)
    def test_attachment_rules_and_private_download(self):
        self.client.force_login(self.mem); self.client.post(f'/tasks/{self.t.pk}/attach/',{'file':SimpleUploadedFile('x.exe',b'MZ')}); self.assertEqual(TaskAttachment.objects.count(),0)
        self.client.post(f'/tasks/{self.t.pk}/attach/',{'file':SimpleUploadedFile('plan.pdf',b'%PDF-1')}); a=TaskAttachment.objects.get(); self.assertRaises(ValueError,lambda:a.file.url)
        self.assertEqual(b''.join(self.client.get(f'/tasks/attachments/{a.pk}/download/').streaming_content),b'%PDF-1'); self.client.force_login(self.out); self.assertEqual(self.client.get(f'/tasks/attachments/{a.pk}/download/').status_code,404); self.client.logout(); self.assertEqual(self.client.get(f'/tasks/attachments/{a.pk}/download/').status_code,302)
class LegalAndNavTests(TestCase):
    def test_legal_pages_and_footer(self):
        for u in('/privacy/','/terms/','/contact/','/partners/','/academy/','/opportunities/'): self.assertEqual(self.client.get(u).status_code,200,u)
        self.assertContains(self.client.get('/'),'/privacy/'); self.assertContains(self.client.get('/privacy/'),'Nigeria Data Protection Act')
    def test_staff_menu_only_shows_permitted_links(self):
        self.client.force_login(mk('plain@x.org')); c=self.client.get('/').content.decode(); self.assertNotIn('/finance/',c); self.assertNotIn('Partner CRM',c); self.assertIn('/dashboard/',c)
