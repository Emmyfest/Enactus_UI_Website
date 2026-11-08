from django import forms
from django.contrib.auth.decorators import login_required,permission_required
from django.db import transaction
from django.shortcuts import get_object_or_404,redirect,render
from django.utils import timezone
from django.views.decorators.http import require_POST
from apps.core.audit import record
from .models import Application,Department,RecruitmentPeriod
class ApplicationForm(forms.ModelForm):
    class Meta:
        model=Application; fields=('full_name','email','phone','matric_number','faculty','department','level','skills','motivation')
    def __init__(self,*a,**k):
        super().__init__(*a,**k); self.fields['department'].queryset=Department.objects.filter(is_active=True)
def apply(request):
    period=RecruitmentPeriod.current()
    if not period: return render(request,'message.html',{'title':'Recruitment is currently closed','text':'No recruitment period is open. Please check back later.'})
    form=ApplicationForm(request.POST or None)
    if request.method=='POST' and form.is_valid():
        a=form.save(commit=False); a.period=period; a.save(); record(None,'application.submitted',a,request=request)
        return render(request,'message.html',{'title':'Application received','text':f'Your reference is {a.reference}. Keep it for follow-up.'})
    return render(request,'form.html',{'form':form,'title':'Join Enactus UI','submit':'Submit application'})
@login_required
@permission_required('members.review_application',raise_exception=True)
def review(request):
    qs=Application.objects.select_related('department','period')
    s=request.GET.get('status')
    if s: qs=qs.filter(status=s)
    return render(request,'members/review.html',{'apps':qs[:200],'statuses':Application.STATUS,'current':s})
@login_required
@permission_required('members.review_application',raise_exception=True)
@require_POST
def decide(request,pk):
    d=request.POST.get('decision')
    if d not in {'shortlisted','interview','accepted','rejected'}: return render(request,'message.html',{'title':'Invalid decision','text':''},status=400)
    with transaction.atomic():
        a=get_object_or_404(Application.objects.select_for_update(),pk=pk)
        a.status=d; a.reviewed_by=request.user; a.reviewed_at=timezone.now(); a.decision_note=request.POST.get('note','')[:1000]; a.save()
        record(request.user,f'application.{d}',a,a.decision_note,request)
    return redirect('review')
