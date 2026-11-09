from django.contrib import admin
from .models import Enquiry,Interaction,Partner
class II(admin.TabularInline): model=Interaction; extra=0
@admin.register(Partner)
class PA(admin.ModelAdmin): list_display=('name','status','expires','is_public','responsible_officer'); list_filter=('status','is_public'); inlines=[II]
@admin.register(Enquiry)
class EA(admin.ModelAdmin):
    list_display=('name','kind','status','created'); list_filter=('kind','status')
    def has_delete_permission(self,r,o=None): return False
