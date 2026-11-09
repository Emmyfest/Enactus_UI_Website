from django.contrib import admin
from .models import Opportunity
@admin.register(Opportunity)
class OA(admin.ModelAdmin):
    list_display=('name','organiser','category','deadline','status','is_published'); list_filter=('category','status','is_published')
