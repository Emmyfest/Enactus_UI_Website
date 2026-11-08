from django.contrib import admin
from .models import Announcement,Notification
admin.site.register([Announcement,Notification])
