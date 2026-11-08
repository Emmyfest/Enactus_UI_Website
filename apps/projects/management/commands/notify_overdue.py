from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.comms.models import Notification
from apps.comms.notify import notify
from apps.projects.models import Task
class Command(BaseCommand):
    help='Notify assignees of overdue tasks (idempotent). Schedule daily with a Render cron job.'
    def handle(self,*a,**k):
        n=0
        for t in Task.objects.exclude(status='done').filter(due__lt=timezone.localdate(),assignee__isnull=False).select_related('assignee','project'):
            msg=f'Overdue: {t.title} ({t.project.name}, due {t.due})'
            if not Notification.objects.filter(user=t.assignee,message=msg,read=False).exists(): notify(t.assignee,msg,f'/projects/{t.project.slug}/'); n+=1
        self.stdout.write(f'{n} reminders sent')
