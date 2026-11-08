from django.contrib import admin
from .models import Administration,Appointment,Position
admin.site.register([Position,Administration,Appointment])
