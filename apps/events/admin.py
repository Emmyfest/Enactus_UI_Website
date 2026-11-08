from django.contrib import admin
from .models import Attendance,Event,Registration
@admin.register(Event)
class EA(admin.ModelAdmin): list_display=('title','starts','is_published'); prepopulated_fields={'slug':('title',)}
admin.site.register([Registration,Attendance])
