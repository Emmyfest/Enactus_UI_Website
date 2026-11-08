from django.conf import settings
from django.db import models
class Announcement(models.Model):
    AUD=[('public','Public (everyone)'),('members','Signed-in users'),('roles','Selected roles only')]
    title=models.CharField(max_length=200); body=models.TextField(); audience=models.CharField(max_length=10,choices=AUD,default='members')
    roles=models.ManyToManyField('accounts.Role',blank=True,help_text='Used when audience is "Selected roles only"')
    author=models.ForeignKey(settings.AUTH_USER_MODEL,null=True,on_delete=models.SET_NULL,related_name='+'); created=models.DateTimeField(auto_now_add=True)
    class Meta: ordering=['-created']
    def __str__(self): return self.title
class Notification(models.Model):
    user=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.CASCADE,related_name='notifications')
    message=models.CharField(max_length=300); url=models.CharField(max_length=200,blank=True); read=models.BooleanField(default=False); created=models.DateTimeField(auto_now_add=True)
    class Meta: ordering=['-created']; indexes=[models.Index(fields=['user','read'])]
