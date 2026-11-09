from django.contrib import admin
from .models import Document,DocumentVersion
@admin.register(Document)
class DA(admin.ModelAdmin):
    list_display=('title','category','access','is_archived'); list_filter=('category','access','is_archived'); filter_horizontal=('roles',)
    def has_delete_permission(self,r,o=None): return False
@admin.register(DocumentVersion)
class VA(admin.ModelAdmin):
    list_display=('document','number','uploaded_by','uploaded_at')
    def has_add_permission(self,r): return False
    def has_change_permission(self,r,o=None): return False
    def has_delete_permission(self,r,o=None): return False
