from django.conf import settings
from django.db import models
from django.utils import timezone
U=settings.AUTH_USER_MODEL
STAGES=[(s,s.replace('_',' ').title()) for s in('ideation','research','feasibility','business_model','prototype','pilot','implementation','monitoring','scaling','completed','suspended','archived')]
class ProjectCategory(models.Model):
    name=models.CharField(max_length=100,unique=True)
    class Meta: verbose_name_plural='project categories'
    def __str__(self): return self.name
class Project(models.Model):
    name=models.CharField(max_length=150); slug=models.SlugField(unique=True); summary=models.TextField(blank=True)
    problem=models.TextField(blank=True); solution=models.TextField(blank=True); beneficiaries=models.TextField(blank=True); location=models.CharField(max_length=150,blank=True)
    category=models.ForeignKey(ProjectCategory,null=True,blank=True,on_delete=models.PROTECT); stage=models.CharField(max_length=20,choices=STAGES,default='ideation',db_index=True)
    manager=models.ForeignKey(U,null=True,blank=True,on_delete=models.PROTECT,related_name='managed_projects')
    is_public=models.BooleanField(default=False); start_date=models.DateField(null=True,blank=True); expected_end=models.DateField(null=True,blank=True); created=models.DateTimeField(auto_now_add=True)
    class Meta: ordering=['name']
    def __str__(self): return self.name
class ProjectMember(models.Model):
    project=models.ForeignKey(Project,on_delete=models.CASCADE,related_name='members'); user=models.ForeignKey(U,on_delete=models.PROTECT,related_name='project_memberships'); role=models.CharField(max_length=80,blank=True)
    class Meta: constraints=[models.UniqueConstraint(fields=['project','user'],name='uniq_project_member')]
class Milestone(models.Model):
    project=models.ForeignKey(Project,on_delete=models.CASCADE,related_name='milestones'); title=models.CharField(max_length=150); due=models.DateField(null=True,blank=True); done=models.BooleanField(default=False)
    class Meta: ordering=['due']
    def __str__(self): return self.title
class Task(models.Model):
    PRIORITY=[('low','Low'),('medium','Medium'),('high','High')]; STATUS=[('todo','To do'),('doing','In progress'),('done','Done')]
    project=models.ForeignKey(Project,on_delete=models.CASCADE,related_name='tasks'); title=models.CharField(max_length=200); description=models.TextField(blank=True)
    assignee=models.ForeignKey(U,null=True,blank=True,on_delete=models.SET_NULL,related_name='tasks'); priority=models.CharField(max_length=8,choices=PRIORITY,default='medium')
    due=models.DateField(null=True,blank=True); status=models.CharField(max_length=6,choices=STATUS,default='todo',db_index=True)
    milestone=models.ForeignKey(Milestone,null=True,blank=True,on_delete=models.SET_NULL); completed_at=models.DateTimeField(null=True,blank=True); created=models.DateTimeField(auto_now_add=True)
    class Meta: ordering=['due','-created']
    @property
    def is_overdue(self): return bool(self.due and self.status!='done' and self.due<timezone.localdate())
