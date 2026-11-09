from django.conf import settings
from django.core.validators import MaxValueValidator,MinValueValidator
from django.db import models
from django.db.models import Q
U=settings.AUTH_USER_MODEL
class Course(models.Model):
    CAT=[(c,c.replace('_',' ').title()) for c in('entrepreneurship','design_thinking','business_model','financial_literacy','project_management','leadership','pitching','research','technical','sustainability','grant_writing','fundraising','report_writing','other')]
    title=models.CharField(max_length=200); slug=models.SlugField(unique=True); description=models.TextField(blank=True); category=models.CharField(max_length=20,choices=CAT,default='other')
    trainer=models.ForeignKey(U,null=True,blank=True,on_delete=models.SET_NULL,related_name='courses_taught'); is_published=models.BooleanField(default=False); created=models.DateTimeField(auto_now_add=True)
    class Meta: ordering=['title']; permissions=[('manage_academy','Can manage any course and its enrolments'),('issue_certificate','Can issue certificates')]
    def __str__(self): return self.title
class CourseResource(models.Model):
    KIND=[('pdf','PDF or document link'),('video','Video link'),('link','Web link'),('assignment','Assignment')]
    course=models.ForeignKey(Course,on_delete=models.CASCADE,related_name='resources'); title=models.CharField(max_length=200); kind=models.CharField(max_length=10,choices=KIND,default='link')
    url=models.URLField(blank=True); instructions=models.TextField(blank=True); order=models.PositiveIntegerField(default=0)
    class Meta: ordering=['order','id']
    def __str__(self): return self.title
class Enrolment(models.Model):
    course=models.ForeignKey(Course,on_delete=models.CASCADE,related_name='enrolments'); user=models.ForeignKey(U,on_delete=models.PROTECT,related_name='enrolments')
    status=models.CharField(max_length=10,default='enrolled'); score=models.DecimalField(max_digits=5,decimal_places=2,null=True,blank=True,validators=[MinValueValidator(0),MaxValueValidator(100)])
    completed_at=models.DateTimeField(null=True,blank=True); certificate_code=models.CharField(max_length=24,blank=True); certificate_issued_at=models.DateTimeField(null=True,blank=True); created=models.DateTimeField(auto_now_add=True)
    class Meta:
        constraints=[models.UniqueConstraint(fields=['course','user'],name='uniq_enrolment'),models.UniqueConstraint(fields=['certificate_code'],condition=~Q(certificate_code=''),name='uniq_cert_code')]
    @property
    def progress_pct(self):
        t=self.course.resources.count(); return int(100*self.progress.count()/t) if t else 0
class ResourceProgress(models.Model):
    enrolment=models.ForeignKey(Enrolment,on_delete=models.CASCADE,related_name='progress'); resource=models.ForeignKey(CourseResource,on_delete=models.CASCADE); done_at=models.DateTimeField(auto_now_add=True)
    class Meta: constraints=[models.UniqueConstraint(fields=['enrolment','resource'],name='uniq_resource_progress')]
