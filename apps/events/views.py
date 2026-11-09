import csv
import secrets
from io import BytesIO
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required,permission_required
from django.db import transaction
from django.http import Http404,HttpResponse
from django.urls import reverse
from django.shortcuts import get_object_or_404,redirect,render
from django.utils import timezone
from django.views.decorators.http import require_POST
from apps.core.audit import record
from .models import Attendance,Event,Registration
def _event(request,slug):
    e=get_object_or_404(Event,slug=slug)
    if not e.is_published and not request.user.has_perm('events.manage_attendance'): raise Http404
    return e
def event_list(request):
    qs=Event.objects.filter(is_published=True); n=timezone.now()
    return render(request,'events/list.html',{'upcoming':qs.filter(starts__gte=n),'past':qs.filter(starts__lt=n).order_by('-starts')[:20]})
def event_detail(request,slug):
    e=_event(request,slug); u=request.user
    reg=u.is_authenticated and e.registrations.filter(user=u,status='registered').exists(); manage=u.has_perm('events.manage_attendance')
    return render(request,'events/detail.html',{'e':e,'registered':reg,'count':e.registrations.filter(status='registered').count(),'manage':manage,'attendance':e.attendance.select_related('user') if manage else []})
@login_required
@require_POST
def register(request,slug):
    with transaction.atomic():
        e=get_object_or_404(Event.objects.select_for_update(),slug=slug,is_published=True)
        taken=e.registrations.filter(status='registered').count()
        if not e.registration_open: messages.error(request,'Registration for this event has closed.')
        elif e.capacity and taken>=e.capacity: messages.error(request,'This event is full.')
        else:
            Registration.objects.update_or_create(event=e,user=request.user,defaults={'status':'registered'}); messages.success(request,'You are registered.')
    return redirect('event_detail',slug=slug)
@login_required
@permission_required('events.manage_attendance',raise_exception=True)
@require_POST
def checkin(request,slug):
    e=get_object_or_404(Event,slug=slug); u=get_user_model().objects.filter(email__iexact=request.POST.get('email','').strip()).first()
    if not u: messages.error(request,'No account with that email.')
    else:
        _,new=Attendance.objects.get_or_create(event=e,user=u,defaults={'recorded_by':request.user})
        if new: record(request.user,'attendance.recorded',e,u.email,request); messages.success(request,f'{u} checked in.')
        else: messages.info(request,f'{u} was already checked in.')
    return redirect('event_detail',slug=slug)
@login_required
@permission_required('events.manage_attendance',raise_exception=True)
@require_POST
def remove_attendance(request,slug,pk):
    a=get_object_or_404(Attendance,pk=pk,event__slug=slug); record(request.user,'attendance.removed',a.event,a.user.email,request); a.delete()
    return redirect('event_detail',slug=slug)
def _safe(v):
    v=str(v); return "'"+v if v[:1] in '=+-@' else v
@login_required
@permission_required('events.manage_attendance',raise_exception=True)
def attendance_csv(request,slug):
    e=get_object_or_404(Event,slug=slug); r=HttpResponse(content_type='text/csv'); r['Content-Disposition']=f'attachment; filename="{e.slug}-attendance.csv"'
    w=csv.writer(r); w.writerow(['Name','Email','Checked in'])
    for a in e.attendance.select_related('user'): w.writerow([_safe(a.user.full_name),_safe(a.user.email),a.checked_in_at.isoformat()])
    record(request.user,'attendance.exported',e,request=request); return r

@login_required
@permission_required('events.manage_attendance',raise_exception=True)
def qr_svg(request,slug):
    import qrcode
    from qrcode.image.svg import SvgPathImage
    e=get_object_or_404(Event,slug=slug); url=request.build_absolute_uri(reverse('qr_checkin',args=[e.slug,e.checkin_token])); buf=BytesIO()
    qrcode.make(url,image_factory=SvgPathImage,box_size=10).save(buf); return HttpResponse(buf.getvalue(),content_type='image/svg+xml')
@login_required
def qr_checkin(request,slug,token):
    e=get_object_or_404(Event,slug=slug)
    if not secrets.compare_digest(token,e.checkin_token): raise Http404
    if not e.checkin_open: return render(request,'message.html',{'title':'Check-in is closed','text':'Ask an organiser to open check-in.'})
    if request.method=='POST':
        _,new=Attendance.objects.get_or_create(event=e,user=request.user,defaults={'method':'qr'})
        if new: record(request.user,'attendance.qr',e,request.user.email,request)
        return render(request,'message.html',{'title':'You are checked in' if new else 'Already checked in','text':e.title})
    return render(request,'events/qr.html',{'e':e})
@login_required
@permission_required('events.manage_attendance',raise_exception=True)
@require_POST
def checkin_control(request,slug):
    e=get_object_or_404(Event,slug=slug); a=request.POST.get('action')
    if a=='regenerate': e.checkin_token=secrets.token_urlsafe(16)
    elif a in('open','close'): e.checkin_open=(a=='open')
    else: return redirect('event_detail',slug=slug)
    e.save(); record(request.user,f'checkin.{a}',e,request=request); return redirect('event_detail',slug=slug)
