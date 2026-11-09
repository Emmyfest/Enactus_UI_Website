from django import forms
from django.contrib import messages
from django.contrib.auth.decorators import login_required,permission_required
from django.core.cache import cache
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404,redirect,render
from django.utils import timezone
from django.views.decorators.http import require_POST
from apps.comms.notify import notify_perm
from apps.core.audit import record as audit
from apps.core.utils import client_ip
from .models import Enquiry,Interaction,Partner
class EnquiryForm(forms.ModelForm):
    website=forms.CharField(required=False,widget=forms.HiddenInput)   # honeypot: real people leave it empty
    class Meta: model=Enquiry; fields=('kind','name','email','organisation','message')
    def clean_website(self):
        if self.cleaned_data.get('website'): raise forms.ValidationError('Rejected.')
def partners(request):
    t=timezone.localdate(); return render(request,'partnerships/partners.html',{'partners':Partner.objects.filter(is_public=True,status='active').filter(Q(expires__isnull=True)|Q(expires__gte=t))})
def contact(request):
    key=f'enq:{client_ip(request)}'; form=EnquiryForm(request.POST or None,initial={'kind':request.GET.get('kind','general')})
    if request.method=='POST' and form.is_valid():
        if cache.get(key,0)>=5: return HttpResponse('Too many messages. Please try again later.',status=429)
        cache.set(key,cache.get(key,0)+1,3600); e=form.save(); audit(None,'enquiry.received',e,e.kind,request); notify_perm('manage_partnerships',f'New {e.get_kind_display().lower()} from {e.name}','/partnerships/enquiries/')
        return render(request,'message.html',{'title':'Thank you','text':'Your message has been received. We will reply by email.'})
    return render(request,'form.html',{'form':form,'title':'Contact Enactus UI','submit':'Send message'})
@login_required
@permission_required('partnerships.manage_partnerships',raise_exception=True)
def enquiries(request):
    return render(request,'partnerships/enquiries.html',{'items':Enquiry.objects.all()[:200]})
@login_required
@permission_required('partnerships.manage_partnerships',raise_exception=True)
@require_POST
def enquiry_handled(request,pk):
    e=get_object_or_404(Enquiry,pk=pk); e.status='handled'; e.handled_by=request.user; e.handled_at=timezone.now(); e.save(); audit(request.user,'enquiry.handled',e,request=request); return redirect('enquiries')
@login_required
@permission_required('partnerships.manage_partnerships',raise_exception=True)
def crm(request):
    return render(request,'partnerships/crm.html',{'partners':Partner.objects.select_related('responsible_officer'),'today':timezone.localdate()})
@login_required
@permission_required('partnerships.manage_partnerships',raise_exception=True)
def crm_detail(request,pk):
    p=get_object_or_404(Partner,pk=pk)
    if request.method=='POST' and request.POST.get('summary','').strip():
        Interaction.objects.create(partner=p,date=timezone.localdate(),summary=request.POST['summary'].strip()[:2000],recorded_by=request.user); audit(request.user,'partner.interaction',p,request=request); return redirect('crm_detail',pk=pk)
    return render(request,'partnerships/crm_detail.html',{'p':p})
