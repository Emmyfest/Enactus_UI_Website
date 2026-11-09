from .models import Notification
def notify(user,message,url=''): return Notification.objects.create(user=user,message=message[:300],url=url)
def notify_perm(codename,message,url=''):
    """Notify every active user who holds a permission through a role, plus superusers."""
    from django.contrib.auth import get_user_model
    from django.db.models import Q
    for u in get_user_model().objects.filter(is_active=True).filter(Q(is_superuser=True)|Q(roles__is_active=True,roles__permissions__codename=codename)).distinct(): notify(u,message,url)
