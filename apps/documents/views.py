import hashlib
from django import forms
from django.contrib import messages
from django.contrib.auth.decorators import login_required,permission_required
from django.db import transaction
from django.db.models import Q
from django.http import FileResponse,Http404
from django.shortcuts import get_object_or_404,redirect,render
from django.views.decorators.http import require_POST
from apps.core.audit import record
from apps.executives.models import Administration
from .models import Document,DocumentVersion
EXT=('.pdf','.doc','.docx','.xls','.xlsx','.ppt','.pptx','.txt','.csv','.jpg','.jpeg','.png','.webp')
def check(f):
    if not f.name.lower().endswith(EXT): raise forms.ValidationError('Allowed types: PDF, Word, Excel, PowerPoint, text, CSV, JPG, PNG, WebP.')
    if f.size>10*1024*1024: raise forms.ValidationError('Files must be 10 MB or smaller.')
    return f
class DocForm(forms.ModelForm):
    file=forms.FileField(); note=forms.CharField(max_length=300,required=False,label='Version note')
    class Meta: model=Document; fields=('title','description','category','access','roles','project','administration')
    def clean_file(self): return check(self.cleaned_data['file'])
class VersionForm(forms.Form):
    file=forms.FileField(); note=forms.CharField(max_length=300,required=False)
    def clean_file(self): return check(self.cleaned_data['file'])
def manages(u,d): return u.is_authenticated and (d.owner_id==u.pk or u.has_perm('documents.change_document'))
def visible(u,d):
    if d.access=='public': return True
    if not u.is_authenticated: return False
    if manages(u,d) or d.access=='members': return True
    return d.access=='roles' and d.roles.filter(users=u,is_active=True).exists()
def _add_version(d,f,note,user):
    h=hashlib.sha256()
    for c in f.chunks(): h.update(c)
    f.seek(0); n=(d.versions.order_by('-number').values_list('number',flat=True).first() or 0)+1
    return DocumentVersion.objects.create(document=d,number=n,file=f,original_name=f.name[:255],size=f.size,sha256=h.hexdigest(),note=note,uploaded_by=user)
def listing(request):
    u=request.user; qs=Document.objects.filter(is_archived=False).select_related('administration','project')
    if not u.is_authenticated: qs=qs.filter(access='public')
    elif not u.has_perm('documents.change_document'): qs=qs.filter(Q(access__in=['public','members'])|Q(owner=u)|Q(access='roles',roles__in=u.roles.filter(is_active=True))).distinct()
    q=request.GET.get('q','').strip(); c=request.GET.get('category',''); a=request.GET.get('administration','')
    if q: qs=qs.filter(Q(title__icontains=q)|Q(description__icontains=q))
    if c: qs=qs.filter(category=c)
    if a.isdigit(): qs=qs.filter(administration_id=int(a))
    return render(request,'documents/list.html',{'docs':qs[:200],'q':q,'cat':c,'adm':a,'cats':Document.CAT,'admins':Administration.objects.all()})
def detail(request,pk):
    d=get_object_or_404(Document,pk=pk)
    if not visible(request.user,d): raise Http404
    return render(request,'documents/detail.html',{'d':d,'versions':d.versions.all(),'manage':manages(request.user,d),'form':VersionForm()})
@login_required
@permission_required('documents.add_document',raise_exception=True)
def upload(request):
    form=DocForm(request.POST or None,request.FILES or None)
    if request.method=='POST' and form.is_valid():
        with transaction.atomic():
            d=form.save(commit=False); d.owner=request.user; d.save(); form.save_m2m(); v=_add_version(d,form.cleaned_data['file'],form.cleaned_data['note'],request.user)
            record(request.user,'document.uploaded',d,f'v{v.number} {v.sha256[:12]}',request)
        return redirect('document',pk=d.pk)
    return render(request,'form.html',{'form':form,'title':'Upload document','submit':'Upload','multipart':True})
@login_required
@require_POST
def new_version(request,pk):
    with transaction.atomic():
        d=get_object_or_404(Document.objects.select_for_update(),pk=pk)
        if not manages(request.user,d): raise Http404
        f=VersionForm(request.POST,request.FILES)
        if f.is_valid():
            v=_add_version(d,f.cleaned_data['file'],f.cleaned_data['note'],request.user); d.save(); record(request.user,'document.version_added',d,f'v{v.number} {v.sha256[:12]}',request)
        else: messages.error(request,' '.join(x for l in f.errors.values() for x in l))
    return redirect('document',pk=pk)
def download(request,pk,number=None):
    d=get_object_or_404(Document,pk=pk)
    if not visible(request.user,d): raise Http404
    v=get_object_or_404(d.versions,number=number) if number else d.latest
    if not v: raise Http404
    if d.access!='public': record(request.user,'document.downloaded',d,f'v{v.number}',request)
    r=FileResponse(v.file.open('rb'),as_attachment=True,filename=v.original_name); r['X-Content-Type-Options']='nosniff'; return r
@login_required
@require_POST
def archive(request,pk):
    d=get_object_or_404(Document,pk=pk)
    if not manages(request.user,d): raise Http404
    d.is_archived=not d.is_archived; d.save(); record(request.user,'document.archived' if d.is_archived else 'document.restored',d,request=request); return redirect('document',pk=pk)
