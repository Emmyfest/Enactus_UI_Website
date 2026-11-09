from django.db.models import Q
from django.urls import reverse
from django.utils import timezone
def run(u,q):
    from apps.academy.models import Course
    from apps.comms.models import Announcement
    from apps.documents.models import Document
    from apps.documents.views import visible as doc_visible
    from apps.events.models import Event
    from apps.members.models import MemberProfile
    from apps.network.models import AlumniProfile
    from apps.opportunities.models import Opportunity
    from apps.partnerships.models import Partner
    from apps.projects.models import Project
    from apps.projects.views import can_manage,is_member
    out=[]; L=lambda s,rows: out.append((s,rows)) if rows else None; t=timezone.localdate()
    L('Projects',[(p.name,reverse('project_detail',args=[p.slug]),p.get_stage_display()) for p in Project.objects.filter(Q(name__icontains=q)|Q(summary__icontains=q))[:40] if p.is_public or can_manage(u,p) or is_member(u,p)][:10])
    ev=Event.objects.filter(title__icontains=q)
    if not u.has_perm('events.manage_attendance'): ev=ev.filter(is_published=True)
    L('Events',[(e.title,reverse('event_detail',args=[e.slug]),e.starts.strftime('%d %b %Y')) for e in ev[:10]])
    L('Opportunities',[(o.name,reverse('opportunity',args=[o.pk]),o.state) for o in Opportunity.objects.filter(is_published=True).filter(Q(name__icontains=q)|Q(organiser__icontains=q))[:10]])
    L('Courses',[(c.title,reverse('course',args=[c.slug]),c.get_category_display()) for c in Course.objects.filter(is_published=True,title__icontains=q)[:10]])
    L('Documents',[(d.title,reverse('document',args=[d.pk]),d.get_category_display()) for d in Document.objects.filter(is_archived=False).filter(Q(title__icontains=q)|Q(description__icontains=q))[:60] if doc_visible(u,d)][:10])
    an=Announcement.objects.filter(Q(title__icontains=q)|Q(body__icontains=q))
    an=an.filter(audience='public') if not u.is_authenticated else an.filter(Q(audience__in=['public','members'])|Q(audience='roles',roles__in=u.roles.all())).distinct()
    L('Announcements',[(a.title,reverse('news'),a.created.strftime('%d %b %Y')) for a in an[:10]])
    L('Alumni',[(a.user.full_name,reverse('alumni'),a.department) for a in AlumniProfile.objects.filter(is_approved=True,public_profile=True,user__full_name__icontains=q).select_related('user')[:10]])
    pt=Partner.objects.filter(name__icontains=q)
    if u.has_perm('partnerships.manage_partnerships'): L('Partners',[(p.name,reverse('crm_detail',args=[p.pk]),p.get_status_display()) for p in pt[:10]])
    else: L('Partners',[(p.name,reverse('partners'),p.category) for p in pt.filter(is_public=True,status='active').filter(Q(expires__isnull=True)|Q(expires__gte=t))[:10]])
    if u.has_perm('members.view_memberprofile'): L('Members',[(m.user.full_name,reverse('members_list')+f'?q={m.user.email}',m.get_status_display()) for m in MemberProfile.objects.filter(Q(user__full_name__icontains=q)|Q(user__email__icontains=q)).select_related('user')[:10]])
    return out
