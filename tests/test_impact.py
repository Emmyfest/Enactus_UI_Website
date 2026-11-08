import tempfile
from datetime import date
from decimal import Decimal
from django.contrib.auth.models import Permission
from django.core.exceptions import PermissionDenied
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase,override_settings
from apps.accounts.models import Role,User
from apps.comms.models import Notification
from apps.core.models import AuditLog
from apps.impact.models import ImpactRecord,ImpactSnapshot,ProjectReport
from apps.projects.models import Project,ProjectMember
PW='Str0ng-pass-ph4se!'
def mk(e): return User.objects.create_user(e,PW,full_name=e.split('@')[0].title())
def grant(u,*codes):
    r=Role.objects.create(name=f'r{u.pk}',slug=f'r{u.pk}'); r.permissions.add(*Permission.objects.filter(codename__in=codes)); u.roles.add(r)
BASE=dict(indicator='People trained',category='output',period_start='2026-01-01',period_end='2026-03-31',actual='40',unit='people',method='Attendance registers')
class Base(TestCase):
    def setUp(self):
        self.mgr,self.mem,self.out,self.ver=mk('mgr@x.org'),mk('mem@x.org'),mk('out@x.org'),mk('ver@x.org'); grant(self.ver,'verify_impact','review_report')
        self.p=Project.objects.create(name='P',slug='p',is_public=True,manager=self.mgr); ProjectMember.objects.create(project=self.p,user=self.mem)
    def rec(self,status='draft',officer=None,**k):
        d=dict(project=self.p,indicator='X',category='direct',period_start=date(2026,1,1),period_end=date(2026,3,31),actual=Decimal('10'),unit='people',method='m',reporting_officer=officer or self.mem,status=status); d.update(k); return ImpactRecord.objects.create(**d)
    def act(self,user,r,action,note=''): self.client.force_login(user); return self.client.post(f'/impact/records/{r.pk}/action/',{'action':action,'note':note})
class WorkflowTests(Base):
    def test_team_creates_draft_outsider_cannot(self):
        self.client.force_login(self.out); self.assertEqual(self.client.post('/impact/projects/p/records/new/',BASE).status_code,403)
        self.client.force_login(self.mem); self.client.post('/impact/projects/p/records/new/',BASE); r=ImpactRecord.objects.get(); self.assertEqual((r.status,r.reporting_officer),('draft',self.mem))
    def test_period_validation(self):
        self.client.force_login(self.mem); self.client.post('/impact/projects/p/records/new/',{**BASE,'period_end':'2025-01-01'}); self.assertEqual(ImpactRecord.objects.count(),0)
    def test_submit_notifies_verifiers_and_cannot_skip_review(self):
        r=self.rec(); self.act(self.mem,r,'approved'); r.refresh_from_db(); self.assertEqual(r.status,'draft')
        self.act(self.mem,r,'submitted'); r.refresh_from_db(); self.assertEqual(r.status,'submitted'); self.assertTrue(Notification.objects.filter(user=self.ver,message__startswith='Awaiting').exists())
    def test_reporter_cannot_verify_own_record(self):
        grant(self.mem,'verify_impact'); r=self.rec('submitted'); self.act(self.mem,r,'approved'); self.assertEqual(self.act(self.mem,r,'approved').status_code,403)
    def test_non_verifier_cannot_approve(self):
        r=self.rec('submitted'); self.assertEqual(self.act(self.mgr,r,'approved').status_code,403)
    def test_approval_snapshots_audits_notifies(self):
        r=self.rec('submitted'); self.act(self.ver,r,'approved'); r.refresh_from_db(); self.assertEqual((r.status,r.verified_by),('approved',self.ver))
        s=ImpactSnapshot.objects.get(); self.assertEqual(s.actual,Decimal('10')); self.assertTrue(AuditLog.objects.filter(action='impactrecord.approved').exists()); self.assertTrue(Notification.objects.filter(user=self.mem,message__contains='approved').exists())
    def test_rejection_and_correction_need_a_note(self):
        r=self.rec('submitted'); self.act(self.ver,r,'rejected'); r.refresh_from_db(); self.assertEqual(r.status,'submitted')
        self.act(self.ver,r,'requires_correction','Fix the unit'); r.refresh_from_db(); self.assertEqual(r.status,'requires_correction')
        self.act(self.mem,r,'submitted'); r.refresh_from_db(); self.assertEqual(r.status,'submitted')
    def test_edit_logs_old_and_new_values(self):
        r=self.rec(); self.client.force_login(self.mem); self.client.post(f'/impact/records/{r.pk}/edit/',{**BASE,'actual':'55'})
        self.assertTrue(AuditLog.objects.filter(action='impact.changed',detail__contains='10.00 -> 55').exists())
class IntegrityTests(Base):
    def test_approved_record_is_locked(self):
        r=self.rec('submitted'); self.act(self.ver,r,'approved'); r.refresh_from_db(); r.actual=Decimal('999'); self.assertRaises(PermissionDenied,r.save); self.assertRaises(PermissionDenied,r.delete)
        self.client.force_login(self.mem); self.assertEqual(self.client.post(f'/impact/records/{r.pk}/edit/',{**BASE,'actual':'999'}).status_code,403)
    def test_snapshots_immutable(self):
        r=self.rec('submitted'); self.act(self.ver,r,'approved'); s=ImpactSnapshot.objects.get(); s.actual=Decimal('1'); self.assertRaises(PermissionDenied,s.save); self.assertRaises(PermissionDenied,s.delete); self.assertRaises(PermissionDenied,ImpactSnapshot.objects.all().update,actual=1)
    def test_approved_report_is_locked(self):
        rp=ProjectReport.objects.create(project=self.p,period_type='monthly',period_start='2026-01-01',period_end='2026-01-31',activities='a',submitted_by=self.mem,status='approved'); rp.activities='changed'; self.assertRaises(PermissionDenied,rp.save)
class DashboardTests(Base):
    def approve(self,**k):
        r=self.rec('submitted',**k); self.act(self.ver,r,'approved'); return r
    def test_only_verified_public_figures_and_categories_kept_apart(self):
        self.approve(indicator='Trained',category='direct'); self.approve(indicator='Expected jobs',category='projection'); self.rec('draft',indicator='DraftOnly'); self.rec('submitted',indicator='PendingOnly')
        r=self.client.get('/impact/'); self.assertContains(r,'Trained'); self.assertContains(r,'Direct impact'); self.assertContains(r,'Projections'); self.assertNotContains(r,'DraftOnly'); self.assertNotContains(r,'PendingOnly')
    def test_private_project_figures_not_public(self):
        priv=Project.objects.create(name='Priv',slug='priv',manager=self.mgr); r=self.rec('submitted',project=priv,indicator='PrivateFigure'); self.act(self.ver,r,'approved'); self.assertNotContains(self.client.get('/impact/'),'PrivateFigure')
    def test_corrected_figure_is_not_double_counted(self):
        old=self.approve(indicator='Trained',actual=Decimal('100')); new=self.rec('submitted',indicator='Trained',actual=Decimal('80'),corrects=old); self.act(self.ver,new,'approved')
        c=self.client.get('/impact/').content.decode(); self.assertIn('80',c); self.assertNotIn('180',c); self.assertEqual(ImpactSnapshot.objects.count(),2)
    def test_drafts_hidden_from_public_record_page(self):
        r=self.rec('draft'); self.client.logout(); self.assertEqual(self.client.get(f'/impact/records/{r.pk}/').status_code,404)
class EvidenceTests(Base):
    @override_settings(MEDIA_ROOT=tempfile.mkdtemp())
    def test_file_rules_and_locking(self):
        r=self.rec('draft'); self.client.force_login(self.mem); u=f'/impact/records/{r.pk}/evidence/'
        self.client.post(u,{'description':'bad','file':SimpleUploadedFile('x.exe',b'MZ')}); self.assertEqual(r.evidence.count(),0)
        self.client.post(u,{'description':'Register','file':SimpleUploadedFile('reg.pdf',b'%PDF-1.4')}); self.assertEqual(r.evidence.count(),1)
        self.client.post(u,{'description':'Link only','url':'https://example.org/proof'}); self.assertEqual(r.evidence.count(),2)
        r.status='approved'; ImpactRecord.objects.filter(pk=r.pk).update(status='approved'); self.assertEqual(self.client.post(u,{'description':'late','url':'https://e.org'}).status_code,403)
class ReportTests(Base):
    DATA=dict(period_type='quarterly',period_start='2026-01-01',period_end='2026-03-31',activities='Held workshops')
    def test_report_lifecycle_and_permissions(self):
        self.client.force_login(self.out); self.assertEqual(self.client.post('/impact/projects/p/reports/new/',self.DATA).status_code,403)
        self.client.force_login(self.mem); self.client.post('/impact/projects/p/reports/new/',self.DATA); rp=ProjectReport.objects.get()
        self.client.post(f'/impact/reports/{rp.pk}/action/',{'action':'submitted'}); rp.refresh_from_db(); self.assertEqual(rp.status,'submitted')
        self.assertEqual(self.client.post(f'/impact/reports/{rp.pk}/action/',{'action':'approved'}).status_code,403)
        self.client.force_login(self.ver); self.client.post(f'/impact/reports/{rp.pk}/action/',{'action':'approved'}); rp.refresh_from_db(); self.assertEqual((rp.status,rp.reviewed_by),('approved',self.ver))
    def test_review_queue_requires_permission(self):
        self.client.force_login(self.mem); self.assertEqual(self.client.get('/impact/review/').status_code,403); self.client.force_login(self.ver); self.assertEqual(self.client.get('/impact/review/').status_code,200)
