from django.contrib import admin
from .models import AlumniProfile,FacultyAssignment,FacultyProfile
@admin.register(AlumniProfile)
class AA(admin.ModelAdmin):
    list_display=('user','graduation_year','is_approved','public_profile'); list_filter=('is_approved','public_profile'); actions=['approve']
    @admin.action(description='Approve selected profiles')
    def approve(self,request,qs): qs.update(is_approved=True)
@admin.register(FacultyProfile)
class FA(admin.ModelAdmin):
    list_display=('user','title','is_approved','is_public'); list_filter=('is_approved',); actions=['approve']
    @admin.action(description='Approve selected profiles')
    def approve(self,request,qs): qs.update(is_approved=True)
admin.site.register(FacultyAssignment)
