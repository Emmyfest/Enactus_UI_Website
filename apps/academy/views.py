import secrets
from decimal import Decimal,InvalidOperation
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.http import Http404
from django.shortcuts import get_object_or_404,redirect,render
from django.utils import timezone
from django.views.decorators.http import require_POST
from apps.comms.notify import notify
from apps.core.audit import record as audit
from .models import Course,Enrolment,ResourceProgress
def can_manage(u,c): return u.is_authenticated and (u.has_perm('academy.manage_academy') or c.trainer_id==u.pk)
def course_list(request):
    qs=Course.objects.filter(is_published=True); q=request.GET.get('q','').strip(); cat=request.GET.get('category','')
    if q: qs=qs.filter(Q(title__icontains=q)|Q(description__icontains=q))
    if cat: qs=qs.filter(category=cat)
    return render(request,'academy/list.html',{'courses':qs,'q':q,'cat':cat,'cats':Course.CAT})
def course_detail(request,slug):
    c=get_object_or_404(Course,slug=slug); u=request.user
    if not c.is_published and not can_manage(u,c): raise Http404
    e=Enrolment.objects.filter(course=c,user=u).first() if u.is_authenticated else None
    return render(request,'academy/detail.html',{'c':c,'e':e,'manage':can_manage(u,c),'unlocked':bool(e) or can_manage(u,c),'done':set(e.progress.values_list('resource_id',flat=True)) if e else set()})
@login_required
@require_POST
def enrol(request,slug):
    c=get_object_or_404(Course,slug=slug,is_published=True); _,new=Enrolment.objects.get_or_create(course=c,user=request.user)
    if new: audit(request.user,'academy.enrolled',c,request=request); messages.success(request,'You are enrolled.')
    return redirect('course',slug=slug)
@login_required
@require_POST
def mark(request,slug,pk):
    c=get_object_or_404(Course,slug=slug); e=Enrolment.objects.filter(course=c,user=request.user).first()
    if not e: raise PermissionDenied
    ResourceProgress.objects.get_or_create(enrolment=e,resource=get_object_or_404(c.resources,pk=pk)); return redirect('course',slug=slug)
@login_required
def manage(request,slug):
    c=get_object_or_404(Course,slug=slug)
    if not can_manage(request.user,c): raise PermissionDenied
    return render(request,'academy/manage.html',{'c':c,'enrolments':c.enrolments.select_related('user'),'can_issue':request.user.has_perm('academy.issue_certificate')})
@login_required
@require_POST
def record(request,pk):
    e=get_object_or_404(Enrolment.objects.select_related('course','user'),pk=pk); u=request.user
    if not can_manage(u,e.course): raise PermissionDenied
    a=request.POST.get('action'); raw=request.POST.get('score','').strip()
    if raw:
        try:
            s=Decimal(raw)
            if not 0<=s<=100: raise InvalidOperation
            e.score=s
        except InvalidOperation: messages.error(request,'Score must be a number from 0 to 100.'); return redirect('course_manage',slug=e.course.slug)
    if a=='complete': e.status='completed'; e.completed_at=timezone.now()
    elif a=='certificate':
        if not u.has_perm('academy.issue_certificate'): raise PermissionDenied
        if e.status!='completed': messages.error(request,'Mark the course completed first.'); return redirect('course_manage',slug=e.course.slug)
        if not e.certificate_code: e.certificate_code=secrets.token_hex(6).upper(); e.certificate_issued_at=timezone.now(); notify(e.user,f'Your certificate for {e.course.title} is ready.',f'/academy/{e.course.slug}/')
    e.save(); audit(u,f'academy.{a or "score"}',e,e.user.email,request); return redirect('course_manage',slug=e.course.slug)
def certificate(request,code):
    e=get_object_or_404(Enrolment.objects.select_related('course','user'),certificate_code=code.upper())
    return render(request,'academy/certificate.html',{'e':e})
