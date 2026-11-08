from django import forms
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import Count,Max,Min,Q,Sum
from django.http import Http404
from django.shortcuts import get_object_or_404,redirect,render
from django.utils import timezone
from django.views.decorators.http import require_POST
from apps.comms.notify import notify
from apps.core.audit import record as audit
from apps.projects.models import Project
from apps.projects.views import can_manage,is_member
from . import workflow as wf
from .models import CATEGORY,ImpactEvidence,ImpactRecord,ImpactSnapshot,ProjectReport
D=forms.DateInput(attrs={'type':'date'})
class RecordForm(forms.ModelForm):
    class Meta: model=ImpactRecord; fields=('indicator','category','period_start','period_end','target','actual','unit','beneficiary_category','method','corrects'); widgets={'period_start':D,'period_end':D}
    def __init__(self,*a,project=None,**k):
        super().__init__(*a,**k); self.fields['corrects'].queryset=ImpactRecord.objects.filter(project=project,status='approved') if project else ImpactRecord.objects.none()
    def clean(self):
        c=super().clean()
        if c.get('period_start') and c.get('period_end') and c['period_end']<c['period_start']: raise forms.ValidationError('The period must end after it starts.')
        return c
class ReportForm(forms.ModelForm):
    class Meta: model=ProjectReport; fields=('period_type','period_start','period_end','activities','milestone_progress','challenges','financial_update','beneficiary_engagement','outcomes','evidence_notes','next_steps'); widgets={'period_start':D,'period_end':D}
class EvidenceForm(forms.ModelForm):
    class Meta: model=ImpactEvidence; fields=('description','url','file')
    def clean_file(self):
        f=self.cleaned_data.get('file')
        if f:
            if not f.name.lower().endswith(('.pdf','.jpg','.jpeg','.png','.webp')): raise forms.ValidationError('Only PDF, JPG, PNG or WebP files are accepted.')
            if f.size>5*1024*1024: raise forms.ValidationError('Files must be 5 MB or smaller.')
        return f
    def clean(self):
        c=super().clean()
        if not c.get('url') and not c.get('file'): raise forms.ValidationError('Provide a link or a file.')
        return c
def team(u,p): return u.is_authenticated and (can_manage(u,p) or is_member(u,p))
def _verifiers(perm): return get_user_model().objects.filter(is_active=True).filter(Q(is_superuser=True)|Q(roles__is_active=True,roles__permissions__codename=perm)).distinct()
def dashboard(request):
    snaps=ImpactSnapshot.objects.filter(project__is_public=True).exclude(record__corrections__status='approved')
    rows=snaps.values('category','indicator','unit').annotate(total=Sum('actual'),n=Count('id'),first=Min('period_start'),last=Max('period_end')).order_by('indicator')
    groups=[(label,[r for r in rows if r['category']==key]) for key,label in CATEGORY]
    return render(request,'impact/dashboard.html',{'groups':[g for g in groups if g[1]]})
def _project(request,slug,need_team=True):
    p=get_object_or_404(Project,slug=slug)
    if need_team and not team(request.user,p): raise PermissionDenied
    return p
@login_required
def record_new(request,slug):
    p=_project(request,slug); form=RecordForm(request.POST or None,project=p)
    if request.method=='POST' and form.is_valid():
        r=form.save(commit=False); r.project=p; r.reporting_officer=request.user; r.save(); audit(request.user,'impact.created',r,p.name,request); return redirect('impact_record',pk=r.pk)
    return render(request,'form.html',{'form':form,'title':f'Impact record: {p.name}','submit':'Save draft'})
def _ctx(request,r):
    u=request.user; t=team(u,r.project)
    return {'r':r,'evidence':r.evidence.all() if (t or u.has_perm('impact.verify_impact')) else [],'can_edit':r.status in wf.EDITABLE and u.is_authenticated and (r.reporting_officer_id==u.pk or can_manage(u,r.project)),
      'can_review':u.has_perm('impact.verify_impact') and r.status in('submitted','under_review') and r.reporting_officer_id!=u.pk,'can_evidence':t and r.status in('draft','requires_correction','submitted','under_review'),'form':EvidenceForm()}
def record_detail(request,pk):
    r=get_object_or_404(ImpactRecord.objects.select_related('project'),pk=pk); u=request.user
    if not ((r.status=='approved' and r.project.is_public) or team(u,r.project) or u.has_perm('impact.verify_impact')): raise Http404
    return render(request,'impact/record.html',_ctx(request,r))
@login_required
def record_edit(request,pk):
    r=get_object_or_404(ImpactRecord,pk=pk)
    if not(r.status in wf.EDITABLE and (r.reporting_officer_id==request.user.pk or can_manage(request.user,r.project))): raise PermissionDenied
    form=RecordForm(request.POST or None,instance=r,project=r.project)
    if request.method=='POST' and form.is_valid():
        old={f:str(form.initial.get(f)) for f in form.changed_data}; form.save()
        audit(request.user,'impact.changed',r,'; '.join(f'{f}: {old[f]} -> {getattr(r,f)}' for f in old),request); return redirect('impact_record',pk=r.pk)
    return render(request,'form.html',{'form':form,'title':'Edit impact record','submit':'Save'})
def _apply(request,model,pk,perm_review,url_name,snap=False):
    to=request.POST.get('action'); note=request.POST.get('note','').strip()[:1000]
    with transaction.atomic():
        o=get_object_or_404(model.objects.select_for_update(),pk=pk)
        owner=o.reporting_officer_id if hasattr(o,'reporting_officer_id') else o.submitted_by_id
        if to=='submitted':
            if not(owner==request.user.pk or can_manage(request.user,o.project)): raise PermissionDenied
        elif not request.user.has_perm(perm_review) or owner==request.user.pk: raise PermissionDenied
        if not wf.allowed(o.status,to): messages.error(request,'That change is not allowed from the current status.'); return o
        if to in wf.NEED_NOTE and not note: messages.error(request,'A note is required.'); return o
        o.status=to
        if to!='submitted':
            if snap: o.verified_by=request.user; o.verified_at=timezone.now(); o.verification_note=note
            else: o.reviewed_by=request.user; o.reviewed_at=timezone.now(); o.review_note=note
        o.save()
        if to=='approved' and snap:
            ImpactSnapshot.objects.create(record=o,project=o.project,indicator=o.indicator,category=o.category,period_start=o.period_start,period_end=o.period_end,target=o.target,actual=o.actual,unit=o.unit,method=o.method,approved_by=request.user,approved_at=o.verified_at)
        audit(request.user,f'{model.__name__.lower()}.{to}',o,note,request)
        if to=='submitted':
            for v in _verifiers(perm_review.split('.')[1]): notify(v,f'Awaiting review: {o}',f'/impact/{url_name}/{o.pk}/')
        else: notify(get_user_model().objects.get(pk=owner),f'{o} was {to.replace("_"," ")}',f'/impact/{url_name}/{o.pk}/')
    return o
@login_required
@require_POST
def record_action(request,pk): _apply(request,ImpactRecord,pk,'impact.verify_impact','records',snap=True); return redirect('impact_record',pk=pk)
@login_required
def review_queue(request):
    u=request.user
    if not(u.has_perm('impact.verify_impact') or u.has_perm('impact.review_report')): raise PermissionDenied
    st=['submitted','under_review']
    return render(request,'impact/queue.html',{'records':ImpactRecord.objects.filter(status__in=st).select_related('project') if u.has_perm('impact.verify_impact') else [],'reports':ProjectReport.objects.filter(status__in=st).select_related('project') if u.has_perm('impact.review_report') else []})
@login_required
@require_POST
def evidence_add(request,pk):
    r=get_object_or_404(ImpactRecord,pk=pk)
    if not team(request.user,r.project) or r.status not in('draft','requires_correction','submitted','under_review'): raise PermissionDenied
    f=EvidenceForm(request.POST,request.FILES)
    if f.is_valid():
        e=f.save(commit=False); e.record=r; e.uploaded_by=request.user; e.save(); audit(request.user,'impact.evidence_added',r,e.description,request)
    else: messages.error(request,' '.join(x for l in f.errors.values() for x in l))
    return redirect('impact_record',pk=pk)
@login_required
def report_new(request,slug):
    p=_project(request,slug); form=ReportForm(request.POST or None)
    if request.method=='POST' and form.is_valid():
        r=form.save(commit=False); r.project=p; r.submitted_by=request.user; r.save(); audit(request.user,'projectreport.created',r,p.name,request); return redirect('report_detail',pk=r.pk)
    return render(request,'form.html',{'form':form,'title':f'Project report: {p.name}','submit':'Save draft'})
@login_required
def report_detail(request,pk):
    r=get_object_or_404(ProjectReport.objects.select_related('project'),pk=pk); u=request.user
    if not(team(u,r.project) or u.has_perm('impact.review_report')): raise Http404
    return render(request,'impact/report.html',{'r':r,'can_submit':r.status in wf.EDITABLE and(r.submitted_by_id==u.pk or can_manage(u,r.project)),'can_review':u.has_perm('impact.review_report') and r.status in('submitted','under_review') and r.submitted_by_id!=u.pk})
@login_required
@require_POST
def report_action(request,pk): _apply(request,ProjectReport,pk,'impact.review_report','reports'); return redirect('report_detail',pk=pk)
