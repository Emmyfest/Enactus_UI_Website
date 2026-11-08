from django.contrib import admin
from .models import Application,Department,MemberProfile,RecruitmentPeriod
admin.site.register([Department,RecruitmentPeriod])
@admin.register(MemberProfile)
class MP(admin.ModelAdmin): list_display=('user','status','department'); list_filter=('status','department'); search_fields=('user__full_name','user__email')
@admin.register(Application)
class AP(admin.ModelAdmin): list_display=('reference','full_name','status','created'); list_filter=('status',); search_fields=('reference','full_name','email')
