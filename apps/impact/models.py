from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.core.validators import MinValueValidator
from django.db import models
from apps.core.models import AppendOnlyQuerySet
from apps.projects.models import Project
from .workflow import STATUS
U=settings.AUTH_USER_MODEL
CATEGORY=[('input','Inputs'),('activity','Activities'),('output','Outputs'),('direct','Direct impact'),('indirect','Indirect impact'),('reach','Reach'),('financial','Financial results'),('projection','Projections (not verified results)')]
class LockedWhenApproved(models.Model):
    """Approved records are final. They cannot be edited or deleted; corrections are made with a new record."""
    class Meta: abstract=True
    def save(self,*a,**k):
        if self.pk and type(self).objects.filter(pk=self.pk,status='approved').exists(): raise PermissionDenied('Approved records are locked')
        super().save(*a,**k)
    def delete(self,*a,**k):
        if self.status=='approved': raise PermissionDenied('Approved records cannot be deleted')
        super().delete(*a,**k)
class ProjectReport(LockedWhenApproved):
    PERIOD=[('monthly','Monthly'),('quarterly','Quarterly'),('annual','Annual')]
    project=models.ForeignKey(Project,on_delete=models.PROTECT,related_name='reports'); period_type=models.CharField(max_length=10,choices=PERIOD)
    period_start=models.DateField(); period_end=models.DateField()
    activities=models.TextField(); milestone_progress=models.TextField(blank=True); challenges=models.TextField(blank=True); financial_update=models.TextField(blank=True)
    beneficiary_engagement=models.TextField(blank=True); outcomes=models.TextField(blank=True); evidence_notes=models.TextField(blank=True); next_steps=models.TextField(blank=True)
    status=models.CharField(max_length=20,choices=STATUS,default='draft',db_index=True); submitted_by=models.ForeignKey(U,on_delete=models.PROTECT,related_name='+')
    reviewed_by=models.ForeignKey(U,null=True,blank=True,on_delete=models.SET_NULL,related_name='+'); reviewed_at=models.DateTimeField(null=True,blank=True); review_note=models.TextField(blank=True)
    created=models.DateTimeField(auto_now_add=True)
    class Meta: ordering=['-period_end']; permissions=[('review_report','Can review project reports')]
    def __str__(self): return f'{self.project} {self.get_period_type_display()} {self.period_end}'
class ImpactRecord(LockedWhenApproved):
    project=models.ForeignKey(Project,on_delete=models.PROTECT,related_name='impact_records'); indicator=models.CharField(max_length=200); category=models.CharField(max_length=12,choices=CATEGORY)
    period_start=models.DateField(); period_end=models.DateField(); target=models.DecimalField(max_digits=14,decimal_places=2,null=True,blank=True,validators=[MinValueValidator(0)])
    actual=models.DecimalField(max_digits=14,decimal_places=2,validators=[MinValueValidator(0)]); unit=models.CharField(max_length=60)
    beneficiary_category=models.CharField(max_length=120,blank=True); method=models.TextField(help_text='How this figure was collected')
    reporting_officer=models.ForeignKey(U,on_delete=models.PROTECT,related_name='+'); status=models.CharField(max_length=20,choices=STATUS,default='draft',db_index=True)
    verified_by=models.ForeignKey(U,null=True,blank=True,on_delete=models.SET_NULL,related_name='+'); verified_at=models.DateTimeField(null=True,blank=True); verification_note=models.TextField(blank=True)
    corrects=models.ForeignKey('self',null=True,blank=True,on_delete=models.PROTECT,related_name='corrections'); created=models.DateTimeField(auto_now_add=True)
    class Meta: ordering=['-period_end']; permissions=[('verify_impact','Can verify impact records')]
    def __str__(self): return f'{self.indicator} ({self.period_start} to {self.period_end})'
class ImpactEvidence(models.Model):
    record=models.ForeignKey(ImpactRecord,on_delete=models.PROTECT,related_name='evidence'); description=models.CharField(max_length=250)
    url=models.URLField(blank=True); file=models.FileField(upload_to='evidence/',blank=True); uploaded_by=models.ForeignKey(U,on_delete=models.PROTECT,related_name='+'); created=models.DateTimeField(auto_now_add=True)
class ImpactSnapshot(models.Model):
    """Immutable copy of a figure at the moment it was approved. Public dashboards read only these."""
    record=models.ForeignKey(ImpactRecord,on_delete=models.PROTECT,related_name='snapshots'); project=models.ForeignKey(Project,on_delete=models.PROTECT,related_name='+')
    indicator=models.CharField(max_length=200); category=models.CharField(max_length=12,choices=CATEGORY); period_start=models.DateField(); period_end=models.DateField()
    target=models.DecimalField(max_digits=14,decimal_places=2,null=True); actual=models.DecimalField(max_digits=14,decimal_places=2); unit=models.CharField(max_length=60); method=models.TextField()
    approved_by=models.ForeignKey(U,on_delete=models.PROTECT,related_name='+'); approved_at=models.DateTimeField()
    objects=AppendOnlyQuerySet.as_manager()
    def save(self,*a,**k):
        if self.pk: raise PermissionDenied('Snapshots are immutable')
        super().save(*a,**k)
    def delete(self,*a,**k): raise PermissionDenied('Snapshots are immutable')
