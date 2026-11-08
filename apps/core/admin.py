from django.contrib import admin
from .models import AuditLog,SiteSetting
admin.site.register(SiteSetting)
@admin.register(AuditLog)
class AuditAdmin(admin.ModelAdmin):
    list_display=('at','actor','action','target'); list_filter=('action',); search_fields=('action','target','detail')
    def has_add_permission(self,r): return False
    def has_change_permission(self,r,o=None): return False
    def has_delete_permission(self,r,o=None): return False
