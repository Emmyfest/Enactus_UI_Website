from .models import Notification
def notify(user,message,url=''): return Notification.objects.create(user=user,message=message[:300],url=url)
