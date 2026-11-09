from django.db.models import Count
from django.utils import timezone
def summary_text():
    """Live figures for the handover pack, taken from the database at the moment it is created."""
    from apps.documents.models import Document
    from apps.finance.models import FinancialEntry
    from apps.impact.models import ImpactRecord,ProjectReport
    from apps.members.models import Application,MemberProfile
    from apps.partnerships.models import Partner
    from apps.projects.models import Project,Task
    j=lambda qs,k: ', '.join(f"{r[k]}: {r['n']}" for r in qs) or 'none'; today=timezone.localdate(); st=['submitted','under_review']
    return '\n'.join([f'Generated {timezone.now():%d %b %Y %H:%M}',
      'Projects by stage: '+j(Project.objects.values('stage').annotate(n=Count('id')).order_by('stage'),'stage'),
      f"Open tasks: {Task.objects.exclude(status='done').count()} (overdue: {Task.objects.exclude(status='done').filter(due__lt=today).count()})",
      'Members by status: '+j(MemberProfile.objects.values('status').annotate(n=Count('id')).order_by('status'),'status'),
      f"Applications awaiting review: {Application.objects.filter(status='pending').count()}",
      f"Awaiting approval: finance entries {FinancialEntry.objects.filter(status__in=st).count()}, impact records {ImpactRecord.objects.filter(status__in=st).count()}, project reports {ProjectReport.objects.filter(status__in=st).count()}",
      f"Active partners: {Partner.objects.filter(status='active').count()}",f"Documents in the archive: {Document.objects.filter(is_archived=False).count()}"])
