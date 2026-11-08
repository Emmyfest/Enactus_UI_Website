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
