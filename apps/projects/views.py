from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.http import Http404
from django.shortcuts import get_object_or_404,redirect,render
from django.utils import timezone
from django.views.decorators.http import require_POST
from apps.comms.notify import notify
from apps.core.audit import record
from .models import Project,Task
def can_manage(u,p): return u.is_authenticated and (u.has_perm('projects.change_project') or p.manager_id==u.pk)
def is_member(u,p): return u.is_authenticated and p.members.filter(user=u).exists()
class TaskForm(forms.ModelForm):
    class Meta: model=Task; fields=('title','assignee','priority','due'); widgets={'due':forms.DateInput(attrs={'type':'date'})}
def project_list(request):
    qs=Project.objects.filter(is_public=True).select_related('category'); q=request.GET.get('q','').strip()
    if q: qs=qs.filter(Q(name__icontains=q)|Q(summary__icontains=q))
    return render(request,'projects/list.html',{'projects':qs,'q':q})
def project_detail(request,slug):
    p=get_object_or_404(Project,slug=slug); u=request.user
    if not (p.is_public or can_manage(u,p) or is_member(u,p)): raise Http404
    internal=can_manage(u,p) or is_member(u,p); form=None
    if can_manage(u,p):
        form=TaskForm(); form.fields['assignee'].queryset=get_user_model().objects.filter(project_memberships__project=p)
    from apps.impact.models import ImpactRecord,ProjectReport
    recs=p.impact_records.all() if internal else p.impact_records.filter(status='approved')
    return render(request,'projects/detail.html',{'records':recs,'reports':p.reports.all() if internal else [],'p':p,'internal':internal,'tasks':p.tasks.select_related('assignee') if internal else [],'milestones':p.milestones.all(),'form':form,'manage':can_manage(u,p)})
@login_required
@require_POST
def task_add(request,slug):
    p=get_object_or_404(Project,slug=slug)
    if not can_manage(request.user,p): raise PermissionDenied
    form=TaskForm(request.POST); form.fields['assignee'].queryset=get_user_model().objects.filter(project_memberships__project=p)
    if form.is_valid():
        t=form.save(commit=False); t.project=p; t.save(); record(request.user,'task.created',t,p.name,request)
        if t.assignee: notify(t.assignee,f'New task on {p.name}: {t.title}',f'/projects/{p.slug}/')
    return redirect('project_detail',slug=slug)
@login_required
@require_POST
def task_status(request,pk):
    t=get_object_or_404(Task.objects.select_related('project'),pk=pk)
    if not (can_manage(request.user,t.project) or t.assignee_id==request.user.pk): raise PermissionDenied
    s=request.POST.get('status')
    if s in dict(Task.STATUS):
        t.status=s; t.completed_at=timezone.now() if s=='done' else None; t.save(); record(request.user,'task.status',t,s,request)
    return redirect('project_detail',slug=t.project.slug)
