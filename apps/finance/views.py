from collections import defaultdict
from decimal import Decimal
from django import forms
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import Sum
from django.shortcuts import get_object_or_404,redirect,render
from django.utils import timezone
from django.views.decorators.http import require_POST
from apps.comms.notify import notify
from apps.core.audit import record as audit
from apps.impact import workflow as wf
from .models import FinancialEntry
def need(u,perm):
    if not u.has_perm(perm): raise PermissionDenied
class EntryForm(forms.ModelForm):
    class Meta: model=FinancialEntry; fields=('project','kind','description','amount','date','source','reference','receipt','voids'); widgets={'date':forms.DateInput(attrs={'type':'date'})}
    def __init__(self,*a,**k):
        super().__init__(*a,**k); self.fields['voids'].queryset=FinancialEntry.objects.filter(status='approved'); self.fields['voids'].label='Voids (correct an approved entry)'
    def clean_receipt(self):
        f=self.cleaned_data.get('receipt')
        if f and not f.name.lower().endswith(('.pdf','.jpg','.jpeg','.png','.webp')): raise forms.ValidationError('Only PDF, JPG, PNG or WebP files are accepted.')
        if f and f.size>5*1024*1024: raise forms.ValidationError('Files must be 5 MB or smaller.')
        return f
    def clean(self):
        c=super().clean()
        if c.get('voids') and c.get('amount')!=0: raise forms.ValidationError('An entry that voids another must have an amount of 0.')
        return c
@login_required
def home(request):
    need(request.user,'finance.view_finance')
    live=FinancialEntry.objects.filter(status='approved',voids__isnull=True).exclude(voided_by__status='approved')
    totals={k:Decimal('0') for k,_ in FinancialEntry.KIND}
    for r in live.values('kind').annotate(t=Sum('amount')): totals[r['kind']]=r['t']
    per=defaultdict(lambda:{k:Decimal('0') for k,_ in FinancialEntry.KIND})
    for r in live.values('project__name','kind').annotate(t=Sum('amount')): per[r['project__name'] or 'Organisation-wide'][r['kind']]=r['t']
    rows=[{'name':n,**v,'variance':v['budget']-v['expense']} for n,v in sorted(per.items())]
    return render(request,'finance/home.html',{'totals':[(l,totals[k]) for k,l in FinancialEntry.KIND],'rows':rows,'pending':FinancialEntry.objects.filter(status__in=['submitted','under_review']).count(),'entries':FinancialEntry.objects.select_related('project')[:50]})
@login_required
def entry_new(request):
    need(request.user,'finance.record_finance'); form=EntryForm(request.POST or None,request.FILES or None)
    if request.method=='POST' and form.is_valid():
        e=form.save(commit=False); e.created_by=request.user; e.save(); audit(request.user,'finance.created',e,str(e.amount),request); return redirect('finance_entry',pk=e.pk)
    return render(request,'form.html',{'form':form,'title':'New financial entry','submit':'Save draft','multipart':True})
@login_required
def entry_detail(request,pk):
    need(request.user,'finance.view_finance'); e=get_object_or_404(FinancialEntry.objects.select_related('project'),pk=pk); u=request.user
    return render(request,'finance/entry.html',{'e':e,'can_edit':e.status in wf.EDITABLE and u.has_perm('finance.record_finance'),'can_review':u.has_perm('finance.approve_finance') and e.status in('submitted','under_review') and e.created_by_id!=u.pk})
@login_required
def entry_edit(request,pk):
    e=get_object_or_404(FinancialEntry,pk=pk); need(request.user,'finance.record_finance')
    if e.status not in wf.EDITABLE: raise PermissionDenied
    form=EntryForm(request.POST or None,request.FILES or None,instance=e)
    if request.method=='POST' and form.is_valid():
        old={f:str(form.initial.get(f)) for f in form.changed_data}; form.save(); audit(request.user,'finance.changed',e,'; '.join(f'{f}: {old[f]} -> {getattr(e,f)}' for f in old),request); return redirect('finance_entry',pk=pk)
    return render(request,'form.html',{'form':form,'title':'Edit financial entry','submit':'Save','multipart':True})
@login_required
@require_POST
def entry_action(request,pk):
    to=request.POST.get('action'); note=request.POST.get('note','').strip()[:1000]; u=request.user
    with transaction.atomic():
        e=get_object_or_404(FinancialEntry.objects.select_for_update(),pk=pk)
        if to=='submitted': need(u,'finance.record_finance')
        else:
            need(u,'finance.approve_finance')
            if e.created_by_id==u.pk: raise PermissionDenied
        if not wf.allowed(e.status,to): messages.error(request,'That change is not allowed from the current status.'); return redirect('finance_entry',pk=pk)
        if to in wf.NEED_NOTE and not note: messages.error(request,'A note is required.'); return redirect('finance_entry',pk=pk)
        e.status=to
        if to!='submitted': e.approved_by=u if to=='approved' else e.approved_by; e.approved_at=timezone.now() if to=='approved' else e.approved_at; e.review_note=note
        e.save(); audit(u,f'finance.{to}',e,note,request)
        if to!='submitted': notify(e.created_by,f'Your financial entry was {to.replace("_"," ")}: {e.description}',f'/finance/{e.pk}/')
    return redirect('finance_entry',pk=pk)
