from django.conf import settings
from django.db import models
from django.utils import timezone
class Opportunity(models.Model):
    CAT=[(c,c.replace('_',' ').title()) for c in('grant','competition','fellowship','internship','scholarship','accelerator','incubator','research','challenge','training')]
    name=models.CharField(max_length=200); organiser=models.CharField(max_length=200); category=models.CharField(max_length=15,choices=CAT); description=models.TextField(blank=True); eligibility=models.TextField(blank=True)
    application_url=models.URLField(blank=True); deadline=models.DateField(null=True,blank=True); funding_amount=models.CharField(max_length=120,blank=True); required_documents=models.TextField(blank=True)
    status=models.CharField(max_length=6,choices=[('open','Open'),('closed','Closed')],default='open'); monitoring_officer=models.ForeignKey(settings.AUTH_USER_MODEL,null=True,blank=True,on_delete=models.SET_NULL,related_name='+')
    is_published=models.BooleanField(default=False); created=models.DateTimeField(auto_now_add=True)
    class Meta: ordering=['deadline']; verbose_name_plural='opportunities'
    def __str__(self): return self.name
    @property
    def is_open(self): return self.status=='open' and (self.deadline is None or self.deadline>=timezone.localdate())
    @property
    def state(self): return 'Open' if self.is_open else ('Deadline passed' if self.status=='open' else 'Closed')
