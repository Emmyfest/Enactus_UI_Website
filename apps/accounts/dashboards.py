from django.db import connection
from django.db.models import Count,Q
from django.utils import timezone
from apps.comms.models import Announcement
from apps.core.models import AuditLog
from apps.events.models import Event
from apps.finance.models import FinancialEntry
from apps.impact.models import ImpactRecord,ProjectReport
from apps.members.models import Application,MemberProfile,RecruitmentPeriod
from apps.network.models import AlumniProfile,FacultyAssignment,FacultyProfile
from apps.projects.models import Project,Task
from .models import User
def build(u):
    """Every figure comes from a database query. Sections appear only for the roles that need them."""
    now=timezone.now(); today=timezone.localdate(); c={}
    c['roles']=u.roles.filter(is_active=True); c['profile']=getattr(u,'member_profile',None); c['logins']=u.logins.all()[:5]
    c['my_projects']=Project.objects.filter(members__user=u); c['my_tasks']=Task.objects.filter(assignee=u).exclude(status='done').select_related('project')[:10]
    c['my_events']=Event.objects.filter(registrations__user=u,registrations__status='registered',starts__gte=now)[:5]
    c['announcements']=Announcement.objects.filter(Q(audience__in=['public','members'])|Q(audience='roles',roles__in=u.roles.all())).distinct()[:5]
    c['unread']=u.notifications.filter(read=False).count()
    m=Project.objects.filter(manager=u)
    if m.exists(): c['managed']=m.annotate(open_tasks=Count('tasks',filter=~Q(tasks__status='done')),overdue=Count('tasks',filter=Q(tasks__due__lt=today)&~Q(tasks__status='done')))
    if u.has_perm('members.review_application') or u.has_perm('executives.view_administration'):
        c['exec']={'members':MemberProfile.objects.values('status').annotate(n=Count('id')).order_by('status'),'pending_apps':Application.objects.filter(status='pending').count(),'period':RecruitmentPeriod.current(),
          'stages':Project.objects.values('stage').annotate(n=Count('id')).order_by('stage'),'events':Event.objects.filter(is_published=True,starts__gte=now).count()}
    if hasattr(u,'faculty_profile'):
        ids=FacultyAssignment.objects.filter(user=u).values('project'); st=['submitted','under_review']
        c['faculty']={'projects':Project.objects.filter(pk__in=ids),'records':ImpactRecord.objects.filter(project__in=ids,status__in=st).count(),'reports':ProjectReport.objects.filter(project__in=ids,status__in=st).count()}
    if hasattr(u,'alumni_profile'):
        a=u.alumni_profile; c['alumni']={'approved':a.is_approved,'public':a.public_profile,'mentor':a.mentorship_available,'mentors':AlumniProfile.objects.filter(is_approved=True,mentorship_available=True).count()}
    if u.is_superuser:
        try:
            with connection.cursor() as cur: cur.execute('SELECT 1')
            db=True
        except Exception: db=False
        st=['submitted','under_review']
        c['admin']={'users':User.objects.count(),'unverified':User.objects.filter(email_verified=False).count(),'db_ok':db,'audit':AuditLog.objects.select_related('actor')[:8],
          'pending':[('Membership applications',Application.objects.filter(status='pending').count()),('Alumni profiles',AlumniProfile.objects.filter(is_approved=False).count()),('Faculty profiles',FacultyProfile.objects.filter(is_approved=False).count()),
            ('Financial entries',FinancialEntry.objects.filter(status__in=st).count()),('Impact records',ImpactRecord.objects.filter(status__in=st).count()),('Project reports',ProjectReport.objects.filter(status__in=st).count())]}
    return c
