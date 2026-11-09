import os
from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.core.files.storage import FileSystemStorage
from django.db import models
U=settings.AUTH_USER_MODEL
class PrivateStorage(FileSystemStorage):
    """Documents live outside MEDIA_URL and have no public URL. They are only served by the access-checked download view.
    For production, replace with a PRIVATE object-storage bucket (see README)."""
    @property
    def base_location(self): return settings.PRIVATE_MEDIA_ROOT
    @property
    def location(self): return os.path.abspath(self.base_location)
    @property
    def base_url(self): return None
class Document(models.Model):
    CAT=[(c,l) for c,l in(('annual_report','Annual report'),('project_report','Project report'),('competition','Competition document'),('financial','Financial report'),('policy','Policy'),('minutes','Meeting minutes'),('partnership','Partnership agreement'),('research','Research'),('training','Training material'),('handover','Handover document'),('historical','Historical record'),('other','Other'))]
    ACCESS=[('public','Public'),('members','Signed-in users'),('roles','Selected roles only'),('private','Owner and document managers only')]
    title=models.CharField(max_length=200); description=models.TextField(blank=True); category=models.CharField(max_length=15,choices=CAT,default='other',db_index=True)
    access=models.CharField(max_length=8,choices=ACCESS,default='members'); roles=models.ManyToManyField('accounts.Role',blank=True)
    project=models.ForeignKey('projects.Project',null=True,blank=True,on_delete=models.PROTECT); administration=models.ForeignKey('executives.Administration',null=True,blank=True,on_delete=models.PROTECT)
    owner=models.ForeignKey(U,on_delete=models.PROTECT,related_name='+'); is_archived=models.BooleanField(default=False); created=models.DateTimeField(auto_now_add=True); updated=models.DateTimeField(auto_now=True)
    class Meta: ordering=['-updated']
    def delete(self,*a,**k): raise PermissionDenied('Documents are archived, never deleted')
    def __str__(self): return self.title
    @property
    def latest(self): return self.versions.order_by('-number').first()
class DocumentVersion(models.Model):
    document=models.ForeignKey(Document,on_delete=models.PROTECT,related_name='versions'); number=models.PositiveIntegerField()
    file=models.FileField(upload_to='documents/',storage=PrivateStorage()); original_name=models.CharField(max_length=255); size=models.PositiveBigIntegerField(); sha256=models.CharField(max_length=64)
    note=models.CharField(max_length=300,blank=True); uploaded_by=models.ForeignKey(U,on_delete=models.PROTECT,related_name='+'); uploaded_at=models.DateTimeField(auto_now_add=True)
    class Meta: ordering=['-number']; constraints=[models.UniqueConstraint(fields=['document','number'],name='uniq_doc_version')]
    def save(self,*a,**k):
        if self.pk: raise PermissionDenied('Versions are immutable')
        super().save(*a,**k)
    def delete(self,*a,**k): raise PermissionDenied('Versions cannot be deleted')
