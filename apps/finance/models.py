from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from apps.impact.models import LockedWhenApproved
from apps.impact.workflow import STATUS
from apps.projects.models import Project
U=settings.AUTH_USER_MODEL
class FinancialEntry(LockedWhenApproved):
    """Approved entries are locked. A mistake is corrected by a new entry that voids the old one; nothing is overwritten."""
    KIND=[('budget','Budgeted amount'),('expense','Actual expenditure'),('income','Income received'),('commitment','Outstanding commitment')]
    project=models.ForeignKey(Project,null=True,blank=True,on_delete=models.PROTECT,related_name='finance_entries'); kind=models.CharField(max_length=10,choices=KIND)
    description=models.CharField(max_length=250); amount=models.DecimalField(max_digits=14,decimal_places=2,validators=[MinValueValidator(0)]); date=models.DateField()
    source=models.CharField(max_length=150,blank=True,help_text='Sponsor, grant or payee'); reference=models.CharField(max_length=80,blank=True); receipt=models.FileField(upload_to='receipts/',blank=True)
    status=models.CharField(max_length=20,choices=STATUS,default='draft',db_index=True); created_by=models.ForeignKey(U,on_delete=models.PROTECT,related_name='+')
    approved_by=models.ForeignKey(U,null=True,blank=True,on_delete=models.SET_NULL,related_name='+'); approved_at=models.DateTimeField(null=True,blank=True); review_note=models.TextField(blank=True)
    voids=models.ForeignKey('self',null=True,blank=True,on_delete=models.PROTECT,related_name='voided_by'); created=models.DateTimeField(auto_now_add=True)
    class Meta:
        ordering=['-date','-id']
        permissions=[('record_finance','Can record financial entries'),('approve_finance','Can approve financial entries'),('view_finance','Can view financial records')]
    def __str__(self): return f'{self.get_kind_display()}: {self.description} ({self.amount})'
