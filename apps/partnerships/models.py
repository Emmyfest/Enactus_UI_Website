from django.conf import settings
from django.db import models
U=settings.AUTH_USER_MODEL
class Partner(models.Model):
    STATUS=[('prospect','Prospect'),('active','Active'),('expired','Expired'),('ended','Ended')]
    name=models.CharField(max_length=200); category=models.CharField(max_length=100,blank=True); contact_person=models.CharField(max_length=150,blank=True)
    contact_email=models.EmailField(blank=True); contact_phone=models.CharField(max_length=40,blank=True)   # private: never shown publicly
    partnership_type=models.CharField(max_length=100,blank=True); collaboration_areas=models.TextField(blank=True); status=models.CharField(max_length=10,choices=STATUS,default='prospect')
    started=models.DateField(null=True,blank=True); expires=models.DateField(null=True,blank=True); next_action=models.CharField(max_length=300,blank=True)
    responsible_officer=models.ForeignKey(U,null=True,blank=True,on_delete=models.SET_NULL,related_name='+'); is_public=models.BooleanField(default=False,help_text='Show in the public partner showcase'); created=models.DateTimeField(auto_now_add=True)
    class Meta: ordering=['name']; permissions=[('manage_partnerships','Can see private partner contacts and handle enquiries')]
    def __str__(self): return self.name
class Interaction(models.Model):
    partner=models.ForeignKey(Partner,on_delete=models.CASCADE,related_name='interactions'); date=models.DateField(); summary=models.TextField(); recorded_by=models.ForeignKey(U,null=True,on_delete=models.SET_NULL,related_name='+'); created=models.DateTimeField(auto_now_add=True)
    class Meta: ordering=['-date','-id']
class Enquiry(models.Model):
    KIND=[('general','General enquiry'),('membership','Membership enquiry'),('partnership','Partnership enquiry')]
    kind=models.CharField(max_length=12,choices=KIND,default='general'); name=models.CharField(max_length=150); email=models.EmailField(); organisation=models.CharField(max_length=200,blank=True); message=models.TextField(max_length=3000)
    status=models.CharField(max_length=8,default='new',db_index=True); handled_by=models.ForeignKey(U,null=True,blank=True,on_delete=models.SET_NULL,related_name='+'); handled_at=models.DateTimeField(null=True,blank=True); created=models.DateTimeField(auto_now_add=True)
    class Meta: ordering=['-created']; verbose_name_plural='enquiries'
