import uuid
from django.conf import settings
from django.db import models
from django.db.models import Q
from django.utils import timezone
class Department(models.Model):
    name=models.CharField(max_length=100,unique=True); description=models.TextField(blank=True); is_active=models.BooleanField(default=True)
    def __str__(self): return self.name
class MemberProfile(models.Model):
    STATUS=[(s,s.title()) for s in('applicant','pending','probationary','active','inactive','executive','alumni','suspended','archived')]
    user=models.OneToOneField(settings.AUTH_USER_MODEL,on_delete=models.PROTECT,related_name='member_profile')
    status=models.CharField(max_length=15,choices=STATUS,default='pending',db_index=True)
    matric_number=models.CharField(max_length=30,blank=True); phone=models.CharField(max_length=30,blank=True)  # private fields, never rendered publicly
    faculty=models.CharField(max_length=100,blank=True); department=models.ForeignKey(Department,null=True,blank=True,on_delete=models.PROTECT)
    level=models.CharField(max_length=20,blank=True); skills=models.TextField(blank=True); interests=models.TextField(blank=True)
    photo=models.ImageField(upload_to='members/',blank=True); is_public=models.BooleanField(default=False)
    joined=models.DateField(null=True,blank=True); created=models.DateTimeField(auto_now_add=True)
    class Meta:
        constraints=[models.UniqueConstraint(fields=['matric_number'],condition=~Q(matric_number=''),name='uniq_matric')]
        permissions=[('export_members','Can export member records to CSV'),('view_sensitive','Can see matriculation numbers and phone numbers')]
    def __str__(self): return str(self.user)
class RecruitmentPeriod(models.Model):
    name=models.CharField(max_length=100); opens=models.DateTimeField(); closes=models.DateTimeField(); is_active=models.BooleanField(default=True)
    @classmethod
    def current(cls):
        n=timezone.now(); return cls.objects.filter(is_active=True,opens__lte=n,closes__gte=n).first()
    def __str__(self): return self.name
def _ref(): return 'ENA-'+uuid.uuid4().hex[:8].upper()
class Application(models.Model):
    STATUS=[('pending','Pending'),('shortlisted','Shortlisted'),('interview','Interview'),('accepted','Accepted'),('rejected','Rejected')]
    reference=models.CharField(max_length=20,unique=True,default=_ref,editable=False); period=models.ForeignKey(RecruitmentPeriod,on_delete=models.PROTECT)
    full_name=models.CharField(max_length=150); email=models.EmailField(); phone=models.CharField(max_length=30,blank=True)
    matric_number=models.CharField(max_length=30,blank=True); faculty=models.CharField(max_length=100,blank=True)
    department=models.ForeignKey(Department,null=True,blank=True,on_delete=models.PROTECT); level=models.CharField(max_length=20,blank=True)
    skills=models.TextField(blank=True); motivation=models.TextField()
    status=models.CharField(max_length=12,choices=STATUS,default='pending',db_index=True)
    reviewed_by=models.ForeignKey(settings.AUTH_USER_MODEL,null=True,blank=True,on_delete=models.SET_NULL,related_name='+')
    reviewed_at=models.DateTimeField(null=True,blank=True); decision_note=models.TextField(blank=True,help_text='Internal only')
    interview_at=models.DateTimeField(null=True,blank=True); applicant_message=models.TextField(blank=True,help_text='Shown to the applicant on the status page'); created=models.DateTimeField(auto_now_add=True)
    class Meta:
        ordering=['-created']; permissions=[('review_application','Can review membership applications')]
    def __str__(self): return f'{self.reference} {self.full_name}'
