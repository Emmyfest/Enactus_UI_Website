from django.contrib import admin
from .models import Course,CourseResource,Enrolment
class RI(admin.TabularInline): model=CourseResource; extra=1
@admin.register(Course)
class CA(admin.ModelAdmin): list_display=('title','category','trainer','is_published'); prepopulated_fields={'slug':('title',)}; inlines=[RI]
admin.site.register(Enrolment)
