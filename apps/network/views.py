from django import forms
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404,redirect,render
from apps.impact.models import ImpactRecord,ProjectReport
from .models import AlumniProfile,FacultyAssignment,FacultyProfile
class AlumniForm(forms.ModelForm):
    class Meta: model=AlumniProfile; exclude=('user','is_approved','updated')
def alumni_directory(request):
    qs=AlumniProfile.objects.filter(is_approved=True,public_profile=True).select_related('user'); y=request.GET.get('year','').strip()
    if y.isdigit(): qs=qs.filter(graduation_year=int(y))
    return render(request,'network/alumni.html',{'people':qs,'year':y})
@login_required
def alumni_me(request):
    p=AlumniProfile.objects.filter(user=request.user).first(); form=AlumniForm(request.POST or None,instance=p)
    if request.method=='POST' and form.is_valid():
        o=form.save(commit=False); o.user=request.user; o.is_approved=False; o.save(); messages.success(request,'Saved. Changes are reviewed before anything is shown publicly.'); return redirect('alumni_me')
    return render(request,'form.html',{'form':form,'title':'My alumni profile','submit':'Save','note':'Approved: yes' if p and p.is_approved else 'Awaiting approval before publication.'})
@login_required
def mentors(request):
    return render(request,'network/mentors.html',{'people':AlumniProfile.objects.filter(is_approved=True,mentorship_available=True).select_related('user')})
def advisors(request):
    return render(request,'network/advisors.html',{'people':FacultyProfile.objects.filter(is_approved=True,is_public=True).select_related('user')})
@login_required
def faculty_portal(request):
    if not hasattr(request.user,'faculty_profile'): raise PermissionDenied
    ids=FacultyAssignment.objects.filter(user=request.user).values('project'); st=['submitted','under_review']
    return render(request,'network/faculty.html',{'projects':FacultyAssignment.objects.filter(user=request.user).select_related('project'),
      'records':ImpactRecord.objects.filter(project__in=ids,status__in=st),'reports':ProjectReport.objects.filter(project__in=ids,status__in=st)})
