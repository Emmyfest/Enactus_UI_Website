from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required,permission_required
from django.db.models import Q
from django.shortcuts import get_object_or_404,redirect,render
from django.views.decorators.http import require_POST
from apps.core.audit import record
from .models import Announcement,Notification
class AnnouncementForm(forms.ModelForm):
    class Meta: model=Announcement; fields=('title','body','audience','roles')
def announcements(request):
    qs=Announcement.objects.all()
    if not request.user.is_authenticated: qs=qs.filter(audience='public')
    else: qs=qs.filter(Q(audience__in=['public','members'])|Q(audience='roles',roles__in=request.user.roles.all())).distinct()
    return render(request,'comms/announcements.html',{'items':qs[:50]})
@login_required
@permission_required('comms.add_announcement',raise_exception=True)
def announce(request):
    form=AnnouncementForm(request.POST or None)
    if request.method=='POST' and form.is_valid():
        a=form.save(commit=False); a.author=request.user; a.save(); form.save_m2m()
        U=get_user_model(); users=[]
        if a.audience=='members': users=U.objects.filter(is_active=True)
        elif a.audience=='roles': users=U.objects.filter(is_active=True,roles__in=a.roles.all()).distinct()
        Notification.objects.bulk_create([Notification(user=u,message=f'New announcement: {a.title}',url='/news/') for u in users])
        record(request.user,'announcement.published',a,a.audience,request); return redirect('news')
    return render(request,'form.html',{'form':form,'title':'New announcement','submit':'Publish'})
@login_required
def notifications(request):
    return render(request,'comms/notifications.html',{'items':request.user.notifications.all()[:100]})
@login_required
@require_POST
def mark_read(request,pk=None):
    qs=request.user.notifications.all()
    if pk: qs=qs.filter(pk=pk)
    qs.update(read=True); return redirect('notifications')
