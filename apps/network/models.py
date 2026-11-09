from django.conf import settings
from django.db import models
from apps.projects.models import Project
U=settings.AUTH_USER_MODEL
class AlumniProfile(models.Model):
    """Nothing is public by default. A profile appears only when approved AND the alumnus chose to be public, and each optional field has its own switch."""
    user=models.OneToOneField(U,on_delete=models.PROTECT,related_name='alumni_profile'); graduation_year=models.PositiveSmallIntegerField(null=True,blank=True)
    faculty=models.CharField(max_length=100,blank=True); department=models.CharField(max_length=100,blank=True); previous_positions=models.TextField(blank=True); previous_projects=models.TextField(blank=True)
    skills=models.TextField(blank=True); employer=models.CharField(max_length=150,blank=True); industry=models.CharField(max_length=100,blank=True); achievements=models.TextField(blank=True)
    mentorship_available=models.BooleanField(default=False); public_profile=models.BooleanField(default=False); show_employer=models.BooleanField(default=False)
    show_skills=models.BooleanField(default=False); show_email=models.BooleanField(default=False); is_approved=models.BooleanField(default=False); updated=models.DateTimeField(auto_now=True)
    def __str__(self): return str(self.user)
class FacultyProfile(models.Model):
    user=models.OneToOneField(U,on_delete=models.PROTECT,related_name='faculty_profile'); title=models.CharField(max_length=80,blank=True); department=models.CharField(max_length=100,blank=True)
    bio=models.TextField(blank=True); is_public=models.BooleanField(default=False); is_approved=models.BooleanField(default=False)
    def __str__(self): return str(self.user)
class FacultyAssignment(models.Model):
    """Limits a faculty advisor to specific projects. Users with any assignment can review only those projects."""
    user=models.ForeignKey(U,on_delete=models.CASCADE,related_name='faculty_assignments'); project=models.ForeignKey(Project,on_delete=models.CASCADE,related_name='faculty_assignments')
    class Meta: constraints=[models.UniqueConstraint(fields=['user','project'],name='uniq_faculty_assignment')]
