from django.contrib.auth.signals import user_logged_in
from django.db.models.signals import m2m_changed
from django.dispatch import receiver
from apps.core.audit import record
from apps.core.utils import client_ip
from .models import LoginHistory,User
@receiver(user_logged_in)
def log_login(sender,request,user,**k):
    LoginHistory.objects.create(user=user,ip=client_ip(request),user_agent=request.META.get('HTTP_USER_AGENT','')[:300])
@receiver(m2m_changed,sender=User.roles.through)
def log_roles(sender,instance,action,pk_set,**k):
    if action in('post_add','post_remove','post_clear'): record(None,'user.roles_changed',instance,f'{action}: {sorted(pk_set or [])}')
