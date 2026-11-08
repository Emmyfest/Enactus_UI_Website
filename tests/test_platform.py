from datetime import timedelta
from django.contrib.auth.models import Permission
from django.core.cache import cache
from django.core.exceptions import PermissionDenied
from django.db import IntegrityError,transaction
from django.db.models import ProtectedError
from django.test import TestCase
from django.utils import timezone
from apps.accounts.models import LoginHistory,Role,User
from apps.core.models import AuditLog
from apps.executives.models import Administration,Appointment,Position
from apps.members.models import Application,RecruitmentPeriod
PW='Str0ng-pass-ph4se!'
def mk(email='a@x.org',**k): return User.objects.create_user(email,PW,full_name='Test User',**k)
def reviewer():
    u=mk('rev@x.org'); r=Role.objects.create(name='Sec',slug='sec'); r.permissions.add(Permission.objects.get(codename='review_application')); u.roles.add(r); return u
class AuthTests(TestCase):
    def setUp(self): cache.clear()
    def test_register_gives_no_privileges(self):
        r=self.client.post('/accounts/register/',{'email':'n@x.org','full_name':'New','password1':PW,'password2':PW,'is_staff':'on','roles':'1'})
        u=User.objects.get(email='n@x.org'); self.assertEqual(r.status_code,302); self.assertFalse(u.is_staff); self.assertFalse(u.roles.exists())
    def test_login_logout_and_history(self):
        mk(); self.assertTrue(self.client.post('/accounts/login/',{'username':'a@x.org','password':PW}).status_code==302)
        self.assertEqual(LoginHistory.objects.count(),1); self.assertEqual(self.client.post('/accounts/logout/').status_code,302)
        self.assertEqual(self.client.get('/dashboard/').status_code,302)
    def test_login_throttle(self):
        mk()
        for _ in range(5): self.client.post('/accounts/login/',{'username':'a@x.org','password':'bad'})
        self.assertEqual(self.client.post('/accounts/login/',{'username':'a@x.org','password':PW}).status_code,429)
    def test_password_reset_page(self): self.assertEqual(self.client.get('/accounts/password_reset/').status_code,200)
class PermissionTests(TestCase):
    def test_anonymous_redirected(self): self.assertEqual(self.client.get('/applications/').status_code,302)
    def test_member_forbidden_then_role_grants_access(self):
        u=mk(); self.client.force_login(u); self.assertEqual(self.client.get('/applications/').status_code,403)
        r=Role.objects.create(name='R',slug='r'); r.permissions.add(Permission.objects.get(codename='review_application')); u.roles.add(r)
        self.assertEqual(self.client.get('/applications/').status_code,200)
    def test_inactive_role_grants_nothing(self):
        u=reviewer(); u.roles.update(is_active=False); self.client.force_login(u); self.assertEqual(self.client.get('/applications/').status_code,403)
class RecruitmentTests(TestCase):
    data={'full_name':'Ada','email':'ada@x.org','motivation':'I want to build.'}
    def test_closed_period_creates_nothing(self):
        self.client.post('/join/',self.data); self.assertEqual(Application.objects.count(),0)
    def test_open_period_creates_reference(self):
        n=timezone.now(); RecruitmentPeriod.objects.create(name='P',opens=n-timedelta(days=1),closes=n+timedelta(days=1))
        self.client.post('/join/',self.data); a=Application.objects.get(); self.assertTrue(a.reference.startswith('ENA-'))
    def test_decision_recorded_and_audited(self):
        n=timezone.now(); p=RecruitmentPeriod.objects.create(name='P',opens=n,closes=n+timedelta(days=1))
        a=Application.objects.create(period=p,full_name='Ada',email='a@a.org',motivation='x'); u=reviewer(); self.client.force_login(u)
        self.client.post(f'/applications/{a.pk}/decide/',{'decision':'accepted','note':'good'}); a.refresh_from_db()
        self.assertEqual((a.status,a.reviewed_by),('accepted',u)); self.assertTrue(AuditLog.objects.filter(action='application.accepted').exists())
    def test_non_reviewer_cannot_decide(self):
        n=timezone.now(); p=RecruitmentPeriod.objects.create(name='P',opens=n,closes=n+timedelta(days=1))
        a=Application.objects.create(period=p,full_name='A',email='a@a.org',motivation='x'); self.client.force_login(mk())
        self.assertEqual(self.client.post(f'/applications/{a.pk}/decide/',{'decision':'accepted'}).status_code,403)
class IntegrityTests(TestCase):
    def test_audit_log_is_append_only(self):
        l=AuditLog.objects.create(action='x')
        l.detail='y'; self.assertRaises(PermissionDenied,l.save); self.assertRaises(PermissionDenied,l.delete)
        self.assertRaises(PermissionDenied,AuditLog.objects.all().delete); self.assertRaises(PermissionDenied,AuditLog.objects.all().update,detail='z')
    def test_role_change_is_audited(self):
        u=mk(); u.roles.add(Role.objects.create(name='R',slug='r')); self.assertTrue(AuditLog.objects.filter(action='user.roles_changed').exists())
    def test_single_current_administration(self):
        Administration.objects.create(title='A',start='2025-01-01',is_current=True)
        with self.assertRaises(IntegrityError), transaction.atomic(): Administration.objects.create(title='B',start='2026-01-01',is_current=True)
    def test_history_survives_deactivation_and_is_protected(self):
        u=mk(); ad=Administration.objects.create(title='A',start='2025-01-01'); po=Position.objects.create(title='Team Lead')
        Appointment.objects.create(administration=ad,position=po,user=u,start='2025-01-01'); u.is_active=False; u.save()
        self.assertEqual(Appointment.objects.count(),1); self.assertRaises(ProtectedError,po.delete); self.assertRaises(ProtectedError,u.delete)
class PublicTests(TestCase):
    def test_health_works_for_unknown_host_but_other_pages_do_not(self):
       self.assertEqual(self.client.get('/health/',HTTP_HOST='10.228.24.21:10000').status_code,200)
       self.assertEqual(self.client.get('/',HTTP_HOST='evil.example').status_code,400)       
    def test_pages_and_health(self):
        for url in('/','/leadership/','/join/','/accounts/login/','/health/'): self.assertEqual(self.client.get(url).status_code,200,url)
    def test_only_public_appointments_shown(self):
        ad=Administration.objects.create(title='A',start='2025-01-01',is_current=True); po=Position.objects.create(title='Team Lead')
        Appointment.objects.create(administration=ad,position=po,user=mk('p@x.org'),start='2025-01-01',is_public=True)
        Appointment.objects.create(administration=ad,position=po,user=User.objects.create_user('h@x.org',PW,full_name='Hidden Person'),start='2025-01-01')
        r=self.client.get('/leadership/'); self.assertContains(r,'Test User'); self.assertNotContains(r,'Hidden Person'); self.assertNotContains(r,'h@x.org')
