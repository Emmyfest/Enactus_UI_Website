from django.contrib import admin
from .models import FinancialEntry
@admin.register(FinancialEntry)
class FA(admin.ModelAdmin):
    list_display=('description','kind','amount','status','date'); list_filter=('kind','status')
    def has_delete_permission(self,r,o=None): return False
