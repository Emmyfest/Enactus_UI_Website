from django.shortcuts import render
from .models import Administration
def leadership(request):
    cur=Administration.objects.filter(is_current=True).first()
    appts=cur.appointments.filter(is_public=True).select_related('user','position') if cur else []
    return render(request,'executives/leadership.html',{'admin_term':cur,'appts':appts})
from datetime import timedelta
from django import forms
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.shortcuts import get_object_or_404,redirect
from django.utils import timezone
from django.views.decorators.http import require_POST
from apps.comms.notify import notify_perm
from apps.core.audit import record as audit
from .handover import summary_text
from .models import HandoverItem,HandoverPack
PERMS=('executives.prepare_handover','executives.accept_handover','executives.manage_transition','executives.view_administration')
def _see(u):
    if not any(u.has_perm(p) for p in PERMS): raise PermissionDenied
class ItemForm(forms.ModelForm):
    class Meta: model=HandoverItem; fields=('section','title','content','document')
class PackForm(forms.ModelForm):
    class Meta: model=HandoverPack; fields=('recommendations','lessons_learned','outstanding_obligations','important_contacts')
class TransitionForm(forms.ModelForm):
    class Meta: model=Administration; fields=('title','start'); widgets={'start':forms.DateInput(attrs={'type':'date'})}
@login_required
def handover_home(request):
    _see(request.user); return render(request,'executives/handover_home.html',{'packs':HandoverPack.objects.select_related('administration','prepared_by'),'current':Administration.objects.filter(is_current=True).first()})
@login_required
@require_POST
def handover_new(request):
    if not request.user.has_perm('executives.prepare_handover'): raise PermissionDenied
    cur=Administration.objects.filter(is_current=True).first()
    if not cur: messages.error(request,'There is no current administration.'); return redirect('handover')
    p,new=HandoverPack.objects.get_or_create(administration=cur,defaults={'prepared_by':request.user})
    if new: HandoverItem.objects.create(pack=p,section='summary',title='Live summary at creation',content=summary_text(),added_by=request.user); audit(request.user,'handover.created',p,request=request)
    return redirect('handover_detail',pk=p.pk)
@login_required
def handover_detail(request,pk):
    _see(request.user); p=get_object_or_404(HandoverPack.objects.select_related('administration','prepared_by'),pk=pk); u=request.user
    editable=p.status=='draft' and u.has_perm('executives.prepare_handover'); item_form=ItemForm(); pack_form=PackForm(instance=p)
    if request.method=='POST':
        if not editable: raise PermissionDenied
        if request.POST.get('form')=='pack':
            pack_form=PackForm(request.POST,instance=p)
            if pack_form.is_valid(): pack_form.save(); audit(u,'handover.updated',p,request=request); return redirect('handover_detail',pk=pk)
        else:
            item_form=ItemForm(request.POST)
            if item_form.is_valid(): i=item_form.save(commit=False); i.pack=p; i.added_by=u; i.save(); audit(u,'handover.item_added',p,i.title,request); return redirect('handover_detail',pk=pk)
    return render(request,'executives/handover_detail.html',{'p':p,'items':p.items.select_related('document'),'editable':editable,'item_form':item_form,'pack_form':pack_form,
      'can_submit':editable,'can_accept':p.status=='submitted' and u.has_perm('executives.accept_handover') and p.prepared_by_id!=u.pk})
@login_required
@require_POST
def handover_submit(request,pk):
    p=get_object_or_404(HandoverPack,pk=pk)
    if not request.user.has_perm('executives.prepare_handover') or p.status!='draft': raise PermissionDenied
    p.status='submitted'; p.submitted_at=timezone.now(); p.save(); audit(request.user,'handover.submitted',p,request=request); notify_perm('accept_handover',f'Handover ready for acceptance: {p.administration}',f'/leadership/handover/{p.pk}/'); return redirect('handover_detail',pk=pk)
@login_required
@require_POST
def handover_accept(request,pk):
    p=get_object_or_404(HandoverPack,pk=pk)
    if not request.user.has_perm('executives.accept_handover') or p.status!='submitted' or p.prepared_by_id==request.user.pk: raise PermissionDenied
    p.status='accepted'; p.accepted_by=request.user; p.accepted_at=timezone.now(); p.save(); audit(request.user,'handover.accepted',p,request=request); return redirect('handover_detail',pk=pk)
@login_required
def transition(request):
    if not request.user.has_perm('executives.manage_transition'): raise PermissionDenied
    cur=Administration.objects.filter(is_current=True).first(); form=TransitionForm(request.POST or None)
    if request.method=='POST' and form.is_valid():
        if cur and not (HandoverPack.objects.filter(administration=cur,status='accepted').exists()): messages.error(request,'The current administration needs an accepted handover before it can be closed.')
        else:
            with transaction.atomic():
                if cur: cur.is_current=False; cur.archived=True; cur.end=cur.end or (form.cleaned_data['start']-timedelta(days=1)); cur.save()
                new=form.save(commit=False); new.is_current=True; new.save(); audit(request.user,'administration.transition',new,f'from {cur}',request)
            messages.success(request,'The new administration is now current. Previous records are preserved.'); return redirect('leadership')
    return render(request,'form.html',{'form':form,'title':'Start a new administration','submit':'Close current term and start new','note':f'Closing: {cur}. Requires an accepted handover. Nothing is deleted.' if cur else 'No current administration.'})
