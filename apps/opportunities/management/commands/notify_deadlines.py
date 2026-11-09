from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.comms.models import Notification
from apps.comms.notify import notify
from apps.opportunities.models import Opportunity
class Command(BaseCommand):
    help='Remind monitoring officers of opportunities closing within 7 days (once per day). Schedule daily.'
    def handle(self,*a,**k):
        today=timezone.localdate(); n=0
        for o in Opportunity.objects.filter(status='open',is_published=True,monitoring_officer__isnull=False,deadline__gte=today,deadline__lte=today+timedelta(days=7)):
            msg=f'Deadline reminder: {o.name} closes in {(o.deadline-today).days} day(s)'
            if not Notification.objects.filter(user=o.monitoring_officer,message__startswith=f'Deadline reminder: {o.name}',created__date=today).exists(): notify(o.monitoring_officer,msg,f'/opportunities/{o.pk}/'); n+=1
        self.stdout.write(f'{n} reminders sent')
