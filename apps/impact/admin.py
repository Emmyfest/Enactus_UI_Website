from django.contrib import admin
from .models import ImpactEvidence,ImpactRecord,ImpactSnapshot,ProjectReport
admin.site.register([ImpactRecord,ImpactEvidence,ProjectReport])
@admin.register(ImpactSnapshot)
class SA(admin.ModelAdmin):
    list_display=('indicator','project','actual','unit','approved_at')
    def has_add_permission(self,r): return False
    def has_change_permission(self,r,o=None): return False
    def has_delete_permission(self,r,o=None): return False
