from django.conf import settings
from django.db import models
from django.db.models import Q
class Position(models.Model):
    title=models.CharField(max_length=100,unique=True); rank=models.PositiveIntegerField(default=100); is_active=models.BooleanField(default=True)
    class Meta: ordering=['rank','title']
    def __str__(self): return self.title
class Administration(models.Model):
    """One leadership term. Never reused or overwritten when a new term starts."""
    title=models.CharField(max_length=120,unique=True); start=models.DateField(); end=models.DateField(null=True,blank=True)
    is_current=models.BooleanField(default=False); archived=models.BooleanField(default=False); summary=models.TextField(blank=True)
    class Meta:
        ordering=['-start']; constraints=[models.UniqueConstraint(fields=['is_current'],condition=Q(is_current=True),name='one_current_administration')]
    def __str__(self): return self.title
class Appointment(models.Model):
    administration=models.ForeignKey(Administration,on_delete=models.PROTECT,related_name='appointments')
    position=models.ForeignKey(Position,on_delete=models.PROTECT); user=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT,related_name='appointments')
    start=models.DateField(); end=models.DateField(null=True,blank=True); is_public=models.BooleanField(default=False,help_text='Show on the public leadership page')
    class Meta: ordering=['position__rank']
    def __str__(self): return f'{self.user} / {self.position} / {self.administration}'
from django.core.exceptions import PermissionDenied
class HandoverPack(models.Model):
    """Formal transition record for one administration. Once accepted it is locked."""
    STATUS=[('draft','Draft'),('submitted','Submitted'),('accepted','Accepted')]
    administration=models.OneToOneField(Administration,on_delete=models.PROTECT,related_name='handover'); status=models.CharField(max_length=10,choices=STATUS,default='draft')
    prepared_by=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT,related_name='+'); recommendations=models.TextField(blank=True); lessons_learned=models.TextField(blank=True)
    outstanding_obligations=models.TextField(blank=True); important_contacts=models.TextField(blank=True); created=models.DateTimeField(auto_now_add=True); submitted_at=models.DateTimeField(null=True,blank=True)
    accepted_by=models.ForeignKey(settings.AUTH_USER_MODEL,null=True,blank=True,on_delete=models.SET_NULL,related_name='+'); accepted_at=models.DateTimeField(null=True,blank=True)
    class Meta: permissions=[('prepare_handover','Can prepare the handover pack'),('accept_handover','Can accept a handover pack'),('manage_transition','Can close an administration and start the next')]
    def save(self,*a,**k):
        if self.pk and HandoverPack.objects.filter(pk=self.pk,status='accepted').exists(): raise PermissionDenied('An accepted handover is locked')
        super().save(*a,**k)
    def __str__(self): return f'Handover: {self.administration}'
class HandoverItem(models.Model):
    SECTION=[(s,l) for s,l in(('summary','Auto-generated summary'),('projects','Project status'),('tasks','Pending tasks'),('finance','Financial summary'),('partnerships','Partnership records'),('membership','Membership summary'),('competition','Competition documents'),('annual_report','Annual report'),('policies','Policies'),('other','Other'))]
    pack=models.ForeignKey(HandoverPack,on_delete=models.CASCADE,related_name='items'); section=models.CharField(max_length=15,choices=SECTION,default='other'); title=models.CharField(max_length=200); content=models.TextField(blank=True)
    document=models.ForeignKey('documents.Document',null=True,blank=True,on_delete=models.SET_NULL); added_by=models.ForeignKey(settings.AUTH_USER_MODEL,null=True,on_delete=models.SET_NULL,related_name='+'); created=models.DateTimeField(auto_now_add=True)
    class Meta: ordering=['id']
    def save(self,*a,**k):
        if self.pack.status!='draft': raise PermissionDenied('Only a draft handover can be changed')
        super().save(*a,**k)
