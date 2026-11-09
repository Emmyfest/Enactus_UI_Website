from django.conf import settings
import secrets
from django.db import models
from django.utils import timezone
U=settings.AUTH_USER_MODEL
def new_token(): return secrets.token_urlsafe(16)
class Event(models.Model):
    title=models.CharField(max_length=200); slug=models.SlugField(unique=True); description=models.TextField(blank=True); venue=models.CharField(max_length=200,blank=True)
    starts=models.DateTimeField(db_index=True); ends=models.DateTimeField(null=True,blank=True); registration_deadline=models.DateTimeField(null=True,blank=True)
    capacity=models.PositiveIntegerField(null=True,blank=True); checkin_token=models.CharField(max_length=40,default=new_token,editable=False); checkin_open=models.BooleanField(default=False); is_published=models.BooleanField(default=False); created_by=models.ForeignKey(U,null=True,blank=True,on_delete=models.SET_NULL,related_name='+')
    class Meta: ordering=['starts']; permissions=[('manage_attendance','Can record, correct and export attendance')]
    def __str__(self): return self.title
    @property
    def registration_open(self): return not self.registration_deadline or timezone.now()<=self.registration_deadline
class Registration(models.Model):
    event=models.ForeignKey(Event,on_delete=models.CASCADE,related_name='registrations'); user=models.ForeignKey(U,on_delete=models.PROTECT)
    status=models.CharField(max_length=10,default='registered'); created=models.DateTimeField(auto_now_add=True)
    class Meta: constraints=[models.UniqueConstraint(fields=['event','user'],name='uniq_registration')]
class Attendance(models.Model):
    event=models.ForeignKey(Event,on_delete=models.CASCADE,related_name='attendance'); user=models.ForeignKey(U,on_delete=models.PROTECT)
    checked_in_at=models.DateTimeField(auto_now_add=True); method=models.CharField(max_length=6,default='admin'); recorded_by=models.ForeignKey(U,null=True,on_delete=models.SET_NULL,related_name='+')
    class Meta: constraints=[models.UniqueConstraint(fields=['event','user'],name='uniq_attendance')]
