from django import forms
from django.contrib import messages
from django.contrib.auth.decorators import login_required,permission_required
from django.core.cache import cache
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404,redirect,render
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.views.decorators.http import require_POST
from apps.core.audit import record
from apps.core.csvutil import csv_response
from apps.core.models import setting
from apps.core.utils import client_ip
from .models import Application,Department,MemberProfile,RecruitmentPeriod
from .services import activate_membership
class ApplicationForm(forms.ModelForm):
    class Meta:
        model=Application; fields=('full_name','email','phone','matric_number','faculty','department','level','skills','motivation')
    def __init__(self,*a,**k):
        super().__init__(*a,**k); self.fields['department'].queryset=Department.objects.filter(is_active=True); self.fields['department'].label='Department of interest'
class StatusForm(forms.Form):
    reference=forms.CharField(max_length=20); email=forms.EmailField()
def recruit(request):
    return render(request,'members/recruit.html',{'period':RecruitmentPeriod.current(),'requirements':setting('recruitment_requirements'),'departments':Department.objects.filter(is_active=True)})
def apply(request):
    period=RecruitmentPeriod.current()
    if not period: return render(request,'message.html',{'title':'Recruitment is currently closed','text':'No recruitment period is open. Please check back later, or check an earlier application from the recruitment page.'})
    form=ApplicationForm(request.POST or None)
    if request.method=='POST' and form.is_valid():
        a=form.save(commit=False); a.period=period; a.save(); record(None,'application.submitted',a,request=request)
        return render(request,'message.html',{'title':'Application received','text':f'Your reference is {a.reference}. Keep it safe. Use it with your email on the "Check my application" page to see updates, including interview details and the final decision.'})
    return render(request,'form.html',{'form':form,'title':'Apply to join Enactus UI','submit':'Submit application'})
def status(request):
    form=StatusForm(request.POST or None); result=None; key=f'st:{client_ip(request)}'
    if request.method=='POST':
        if cache.get(key,0)>=10: return HttpResponse('Too many attempts. Try again in 15 minutes.',status=429)
        if form.is_valid():
            result=Application.objects.filter(reference=form.cleaned_data['reference'].strip().upper(),email__iexact=form.cleaned_data['email'].strip()).select_related('department').first()
            if not result: cache.set(key,cache.get(key,0)+1,900); messages.error(request,'No application matches that reference and email.')
    return render(request,'members/status.html',{'form':form,'a':result,'onboarding':setting('onboarding_instructions','') if result and result.status=='accepted' else ''})
@login_required
@permission_required('members.review_application',raise_exception=True)
def review(request):
    qs=Application.objects.select_related('department','period'); s=request.GET.get('status')
    if s: qs=qs.filter(status=s)
    return render(request,'members/review.html',{'apps':qs[:200],'statuses':Application.STATUS,'current':s,'can_export':request.user.has_perm('members.export_members')})
@login_required
@permission_required('members.review_application',raise_exception=True)
@require_POST
def decide(request,pk):
    d=request.POST.get('decision')
    if d not in {'shortlisted','interview','accepted','rejected'}: return render(request,'message.html',{'title':'Invalid decision','text':''},status=400)
    msg=request.POST.get('applicant_message','').strip()[:1500]; at=None; raw=request.POST.get('interview_at','').strip()
    if raw:
        at=parse_datetime(raw)
        if at and timezone.is_naive(at): at=timezone.make_aware(at)
    if d=='interview' and not(at and msg): messages.error(request,'An interview needs a date and a message (venue or link) for the applicant.'); return redirect('review')
    with transaction.atomic():
        a=get_object_or_404(Application.objects.select_for_update(),pk=pk)
        a.status=d; a.reviewed_by=request.user; a.reviewed_at=timezone.now(); a.decision_note=request.POST.get('note','')[:1000]
        if at: a.interview_at=at
        if msg: a.applicant_message=msg
        a.save(); record(request.user,f'application.{d}',a,a.decision_note,request)
        if d=='accepted': activate_membership(a,request)
    return redirect('review')
@login_required
@permission_required('members.review_application',raise_exception=True)
def applications_export(request):
    rows=Application.objects.select_related('department','period'); record(request.user,'applications.exported',None,f'{rows.count()} rows',request)
    return csv_response('applications.csv',['Reference','Name','Email','Phone','Department','Level','Status','Interview','Applied'],[(a.reference,a.full_name,a.email,a.phone,a.department or '',a.level,a.status,a.interview_at or '',a.created.date()) for a in rows])
@login_required
@permission_required('members.view_memberprofile',raise_exception=True)
def members_list(request):
    qs=MemberProfile.objects.select_related('user','department'); q=request.GET.get('q','').strip(); s=request.GET.get('status',''); d=request.GET.get('department','')
    if q: qs=qs.filter(Q(user__full_name__icontains=q)|Q(user__email__icontains=q))
    if s: qs=qs.filter(status=s)
    if d.isdigit(): qs=qs.filter(department_id=int(d))
    return render(request,'members/list.html',{'members':qs[:300],'q':q,'status':s,'dept':d,'statuses':MemberProfile.STATUS,'departments':Department.objects.all(),'can_export':request.user.has_perm('members.export_members'),'sensitive':request.user.has_perm('members.view_sensitive')})
@login_required
@permission_required('members.export_members',raise_exception=True)
def members_export(request):
    qs=MemberProfile.objects.select_related('user','department'); s=request.GET.get('status',''); d=request.GET.get('department','')
    if s: qs=qs.filter(status=s)
    if d.isdigit(): qs=qs.filter(department_id=int(d))
    sens=request.user.has_perm('members.view_sensitive'); head=['Name','Email','Status','Department','Faculty','Level','Joined']+(['Matric number','Phone'] if sens else [])
    rows=[[m.user.full_name,m.user.email,m.status,m.department or '',m.faculty,m.level,m.joined or '']+([m.matric_number,m.phone] if sens else []) for m in qs]
    record(request.user,'members.exported',None,f'{len(rows)} rows; status={s or "all"}; department={d or "all"}; sensitive={sens}',request)
    return csv_response('members.csv',head,rows)
