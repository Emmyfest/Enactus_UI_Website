from .models import Notification
def unread(request):
    u=request.user
    return {'unread_count':Notification.objects.filter(user=u,read=False).count() if u.is_authenticated else 0}
