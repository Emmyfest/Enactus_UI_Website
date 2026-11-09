from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.db import models
class AppendOnlyQuerySet(models.QuerySet):
    def update(self,**k): raise PermissionDenied('The audit log is append-only')
    def bulk_update(self,*a,**k): raise PermissionDenied('The audit log is append-only')
    def delete(self): raise PermissionDenied('The audit log is append-only')
class AuditLog(models.Model):
    actor=models.ForeignKey(settings.AUTH_USER_MODEL,null=True,blank=True,on_delete=models.SET_NULL,related_name='+')
    action=models.CharField(max_length=80,db_index=True); target=models.CharField(max_length=200,blank=True); target_id=models.CharField(max_length=40,blank=True)
    detail=models.TextField(blank=True); ip=models.GenericIPAddressField(null=True,blank=True); at=models.DateTimeField(auto_now_add=True,db_index=True)
    objects=AppendOnlyQuerySet.as_manager()
    class Meta: ordering=['-at']
    def save(self,*a,**k):
        if self.pk: raise PermissionDenied('Audit records cannot be modified')
        super().save(*a,**k)
    def delete(self,*a,**k): raise PermissionDenied('Audit records cannot be deleted')
class SiteSetting(models.Model):
    """Editable public content (about, mission, vision, contact). Nothing here is invented: unset keys show an awaiting-verification notice."""
    key=models.SlugField(unique=True); value=models.TextField(blank=True); is_public=models.BooleanField(default=True)
    def __str__(self): return self.key
def setting(key,default='Awaiting verification: this content has not been supplied yet.'):
    s=SiteSetting.objects.filter(key=key,is_public=True).first(); return s.value if s and s.value else default
class MediaAsset(models.Model):
    CAT=[(c,c.title()) for c in('team','executive','faculty','alumni','project','event','award','partner','training','other')]
    file=models.ImageField(upload_to='library/'); title=models.CharField(max_length=150); alt_text=models.CharField(max_length=250); caption=models.CharField(max_length=300,blank=True)
    category=models.CharField(max_length=10,choices=CAT,default='other',db_index=True); is_public=models.BooleanField(default=False); is_featured=models.BooleanField(default=False)
    uploaded_by=models.ForeignKey(settings.AUTH_USER_MODEL,null=True,on_delete=models.SET_NULL,related_name='+'); created=models.DateTimeField(auto_now_add=True)
    class Meta: ordering=['-is_featured','-created']; permissions=[('manage_media','Can manage the media library')]
    def __str__(self): return self.title
