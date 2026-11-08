from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.models import Permission
class RoleBackend(ModelBackend):
    """Adds the permissions granted through active Roles to Django's normal permission checks."""
    def get_all_permissions(self,user,obj=None):
        perms=set(super().get_all_permissions(user,obj))
        if obj is None and user.is_active and user.pk:
            q=Permission.objects.filter(roles__users=user,roles__is_active=True).values_list('content_type__app_label','codename')
            perms|={f'{a}.{c}' for a,c in q}
        return perms
