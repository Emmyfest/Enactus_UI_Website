from datetime import timedelta
from django.contrib.auth.models import Permission
from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone
from apps.accounts.models import Role,User
from apps.comms.models import Announcement,Notification
from apps.core.models import AuditLog
from apps.events.models import Attendance,Event,Registration
from apps.projects.models import Project,ProjectMember,Task
PW='Str0ng-pass-ph4se!'
def mk(e,**k): return User.objects.create_user(e,PW,full_name=e.split('@')[0].title(),**k)
def with_perm(u,*codes):
    r=Role.objects.create(name=f'r{u.pk}',slug=f'r{u.pk}'); r.permissions.add(*Permission.objects.filter(codename__in=codes)); u.roles.add(r); return r
class ProjectTests(TestCase):
    def setUp(self):
        self.mgr,self.mem,self.out=mk('mgr@x.org'),mk('mem@x.org'),mk('out@x.org')
        self.pub=Project.objects.create(name='Pub',slug='pub',is_public=True,manager=self.mgr); self.priv=Project.objects.create(name='Priv',slug='priv',manager=self.mgr)
        ProjectMember.objects.create(project=self.priv,user=self.mem); ProjectMember.objects.create(project=self.pub,user=self.mem)
    def test_public_list_hides_private(self):
        r=self.client.get('/projects/'); self.assertContains(r,'Pub'); self.assertNotContains(r,'Priv')
    def test_private_detail_only_for_team(self):
        self.assertEqual(self.client.get('/projects/priv/').status_code,404)
        self.client.force_login(self.out); self.assertEqual(self.client.get('/projects/priv/').status_code,404)
        self.client.force_login(self.mem); self.assertEqual(self.client.get('/projects/priv/').status_code,200)
    def test_public_visitor_does_not_see_tasks(self):
        Task.objects.create(project=self.pub,title='SecretTask'); self.assertNotContains(self.client.get('/projects/pub/'),'SecretTask')
    def test_only_manager_creates_tasks_and_assignee_notified(self):
        self.client.force_login(self.mem); self.assertEqual(self.client.post('/projects/priv/tasks/add/',{'title':'T','priority':'low'}).status_code,403)
        self.client.force_login(self.mgr); self.client.post('/projects/priv/tasks/add/',{'title':'T','priority':'low','assignee':self.mem.pk})
        self.assertEqual(Task.objects.count(),1); self.assertTrue(Notification.objects.filter(user=self.mem).exists()); self.assertTrue(AuditLog.objects.filter(action='task.created').exists())
    def test_assignee_updates_own_task_only(self):
        t=Task.objects.create(project=self.priv,title='T',assignee=self.mem); self.client.force_login(self.out)
        self.assertEqual(self.client.post(f'/tasks/{t.pk}/status/',{'status':'done'}).status_code,403)
        self.client.force_login(self.mem); self.client.post(f'/tasks/{t.pk}/status/',{'status':'done'}); t.refresh_from_db(); self.assertEqual(t.status,'done'); self.assertIsNotNone(t.completed_at)
    def test_overdue_reminders_are_not_duplicated(self):
        Task.objects.create(project=self.priv,title='Late',assignee=self.mem,due=timezone.localdate()-timedelta(days=2))
        call_command('notify_overdue'); call_command('notify_overdue'); self.assertEqual(Notification.objects.filter(user=self.mem,message__startswith='Overdue').count(),1)
    def test_permission_holder_can_manage_any_project(self):
        u=mk('lead@x.org'); with_perm(u,'change_project'); self.client.force_login(u)
        self.assertEqual(self.client.post('/projects/priv/tasks/add/',{'title':'X','priority':'low'}).status_code,302)
class EventTests(TestCase):
    def setUp(self):
        n=timezone.now(); self.e=Event.objects.create(title='Ev',slug='ev',starts=n+timedelta(days=2),is_published=True,capacity=1)
        self.u1,self.u2,self.staff=mk('u1@x.org'),mk('u2@x.org'),mk('st@x.org'); with_perm(self.staff,'manage_attendance')
    def test_register_capacity_and_no_duplicates(self):
        self.client.force_login(self.u1); self.client.post('/events/ev/register/'); self.client.post('/events/ev/register/')
        self.client.force_login(self.u2); self.client.post('/events/ev/register/'); self.assertEqual(Registration.objects.filter(event=self.e).count(),1)
    def test_deadline_blocks_registration(self):
        self.e.registration_deadline=timezone.now()-timedelta(hours=1); self.e.capacity=None; self.e.save()
        self.client.force_login(self.u1); self.client.post('/events/ev/register/'); self.assertEqual(Registration.objects.count(),0)
    def test_unpublished_hidden(self):
        Event.objects.create(title='H',slug='h',starts=timezone.now(),is_published=False); self.assertEqual(self.client.get('/events/h/').status_code,404)
    def test_checkin_once_audited_and_restricted(self):
        self.client.force_login(self.u1); self.assertEqual(self.client.post('/events/ev/checkin/',{'email':'u2@x.org'}).status_code,403)
        self.client.force_login(self.staff)
        for _ in range(2): self.client.post('/events/ev/checkin/',{'email':'u2@x.org'})
        self.assertEqual(Attendance.objects.count(),1); self.assertTrue(AuditLog.objects.filter(action='attendance.recorded').exists())
    def test_correction_and_csv_export_protected(self):
        a=Attendance.objects.create(event=self.e,user=self.u2); self.client.force_login(self.u1)
        self.assertEqual(self.client.get('/events/ev/attendance.csv').status_code,403)
        self.client.force_login(self.staff); self.assertEqual(self.client.get('/events/ev/attendance.csv').status_code,200)
        self.client.post(f'/events/ev/attendance/{a.pk}/remove/'); self.assertEqual(Attendance.objects.count(),0); self.assertTrue(AuditLog.objects.filter(action='attendance.removed').exists())
    def test_csv_blocks_formula_injection(self):
        evil=User.objects.create_user('e@x.org',PW,full_name='=HYPERLINK("x")'); Attendance.objects.create(event=self.e,user=evil)
        self.client.force_login(self.staff); self.assertIn("'=HYPERLINK",self.client.get('/events/ev/attendance.csv').content.decode())
class CommsTests(TestCase):
    def test_role_targeting_notifies_only_that_role(self):
        poster,inrole,outside=mk('p@x.org'),mk('in@x.org'),mk('out@x.org'); with_perm(poster,'add_announcement'); tr=Role.objects.create(name='Tgt',slug='tgt'); inrole.roles.add(tr)
        self.client.force_login(poster); self.client.post('/news/new/',{'title':'Hi','body':'b','audience':'roles','roles':[tr.pk]})
        self.assertEqual(Notification.objects.filter(user=inrole).count(),1); self.assertEqual(Notification.objects.filter(user=outside).count(),0)
        self.client.force_login(outside); self.assertNotContains(self.client.get('/news/'),'Hi'); self.client.force_login(inrole); self.assertContains(self.client.get('/news/'),'Hi')
    def test_anonymous_sees_only_public_and_cannot_post(self):
        Announcement.objects.create(title='Pubn',body='x',audience='public'); Announcement.objects.create(title='Memn',body='x',audience='members')
        r=self.client.get('/news/'); self.assertContains(r,'Pubn'); self.assertNotContains(r,'Memn'); self.assertEqual(self.client.get('/news/new/').status_code,302)
    def test_cannot_read_others_notifications(self):
        a,b=mk('a@x.org'),mk('b@x.org'); n=Notification.objects.create(user=a,message='private'); self.client.force_login(b)
        self.assertNotContains(self.client.get('/notifications/'),'private'); self.client.post(f'/notifications/{n.pk}/read/'); n.refresh_from_db(); self.assertFalse(n.read)
