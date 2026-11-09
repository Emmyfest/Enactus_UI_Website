from django.db import connection
from django.http import JsonResponse
from django.shortcuts import render
from .models import MediaAsset,setting
def health(request):
    try:
        with connection.cursor() as c: c.execute('SELECT 1')
        return JsonResponse({'status':'ok'})
    except Exception: return JsonResponse({'status':'unavailable'},status=503)
def home(request):
    return render(request,'home.html',{k:setting(k) for k in ('about','mission','vision')}|{'contact_email':setting('contact_email',''),'featured':MediaAsset.objects.filter(is_public=True,is_featured=True)[:6]})
from django import forms
from django.contrib import messages
from django.contrib.auth.decorators import login_required,permission_required
from django.shortcuts import get_object_or_404,redirect
from django.views.decorators.http import require_POST
from .audit import record as audit
from .models import MediaAsset
def _check(f):
    if not f.name.lower().endswith(('.jpg','.jpeg','.png','.webp')): raise forms.ValidationError('Only JPG, PNG or WebP images are accepted.')
    if f.size>5*1024*1024: raise forms.ValidationError('Images must be 5 MB or smaller.')
    return f
class MediaForm(forms.ModelForm):
    class Meta: model=MediaAsset; fields=('file','title','alt_text','caption','category','is_public','is_featured')
    def clean_file(self): return _check(self.cleaned_data['file'])
class ReplaceForm(forms.Form):
    file=forms.ImageField()
    def clean_file(self): return _check(self.cleaned_data['file'])
def gallery(request):
    c=request.GET.get('category'); qs=MediaAsset.objects.filter(is_public=True)
    if c: qs=qs.filter(category=c)
    return render(request,'media/gallery.html',{'items':qs,'cats':MediaAsset.CAT,'current':c})
@login_required
@permission_required('core.manage_media',raise_exception=True)
def library(request):
    form=MediaForm(request.POST or None,request.FILES or None); c=request.GET.get('category'); qs=MediaAsset.objects.all()
    if c: qs=qs.filter(category=c)
    if request.method=='POST' and form.is_valid():
        a=form.save(commit=False); a.uploaded_by=request.user; a.save(); audit(request.user,'media.uploaded',a,request=request); return redirect('library')
    return render(request,'media/library.html',{'items':qs,'form':form,'cats':MediaAsset.CAT,'current':c})
@login_required
@permission_required('core.manage_media',raise_exception=True)
@require_POST
def media_replace(request,pk):
    a=get_object_or_404(MediaAsset,pk=pk); f=ReplaceForm(request.POST,request.FILES)
    if f.is_valid():
        old=a.file; a.file=f.cleaned_data['file']; a.save(); old.delete(save=False); audit(request.user,'media.replaced',a,request=request)
    else: messages.error(request,' '.join(x for l in f.errors.values() for x in l))
    return redirect('library')
@login_required
@permission_required('core.manage_media',raise_exception=True)
@require_POST
def media_delete(request,pk):
    a=get_object_or_404(MediaAsset,pk=pk)
    if request.POST.get('confirm')!='yes': messages.error(request,'Deletion needs confirmation.'); return redirect('library')
    audit(request.user,'media.deleted',a,a.title,request); f=a.file; a.delete(); f.delete(save=False); return redirect('library')
@login_required
@permission_required('core.manage_media',raise_exception=True)
@require_POST
def media_toggle(request,pk):
    a=get_object_or_404(MediaAsset,pk=pk); field=request.POST.get('field')
    if field in('is_featured','is_public'): setattr(a,field,not getattr(a,field)); a.save(); audit(request.user,f'media.{field}',a,str(getattr(a,field)),request)
    return redirect('library')
def search(request):
    q=request.GET.get('q','').strip(); results=[]
    if len(q)>=2:
        from .search import run
        results=run(request.user,q)
    return render(request,'core/search.html',{'q':q,'results':results,'short':bool(q) and len(q)<2})
def privacy(request): return render(request,'legal/privacy.html',{'contact_email':setting('contact_email','[add contact_email in Site settings]')})
def terms(request): return render(request,'legal/terms.html',{'contact_email':setting('contact_email','[add contact_email in Site settings]')})
