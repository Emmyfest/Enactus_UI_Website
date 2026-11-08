from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as Base
from .models import LoginHistory,Role,User
@admin.register(User)
class UserAdmin(Base):
    ordering=('email',); list_display=('email','full_name','is_active','email_verified'); search_fields=('email','full_name')
    fieldsets=((None,{'fields':('email','password')}),('Profile',{'fields':('full_name','email_verified')}),('Access',{'fields':('is_active','is_staff','is_superuser','roles','groups','user_permissions')}))
    add_fieldsets=((None,{'classes':('wide',),'fields':('email','full_name','password1','password2')}),)
    filter_horizontal=('roles','groups','user_permissions')
@admin.register(Role)
class RoleAdmin(admin.ModelAdmin): filter_horizontal=('permissions',); list_display=('name','is_active')
@admin.register(LoginHistory)
class LoginHistoryAdmin(admin.ModelAdmin):
    list_display=('user','at','ip'); readonly_fields=('user','at','ip','user_agent')
    def has_add_permission(self,r): return False
    def has_change_permission(self,r,o=None): return False
    def has_delete_permission(self,r,o=None): return False
