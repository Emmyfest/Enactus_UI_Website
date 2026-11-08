from django.contrib import admin
from .models import Milestone,Project,ProjectCategory,ProjectMember,Task
class MI(admin.TabularInline): model=ProjectMember
class MS(admin.TabularInline): model=Milestone; extra=0
@admin.register(Project)
class PA(admin.ModelAdmin): list_display=('name','stage','manager','is_public'); list_filter=('stage','is_public','category'); prepopulated_fields={'slug':('name',)}; inlines=[MI,MS]
admin.site.register([ProjectCategory,Task])
