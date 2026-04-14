from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, UserActivityLog


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ['email', 'first_name', 'last_name', 'user_type', 'is_active', 'is_staff', 'date_joined']
    list_filter = ['user_type', 'is_active', 'is_staff', 'is_verified', 'date_joined']
    search_fields = ['email', 'first_name', 'last_name', 'phone']
    ordering = ['-date_joined']
    
    fieldsets = [
        (None, {'fields': ['email', 'password']}),
        ('Personal Info', {'fields': ['first_name', 'last_name', 'phone', 'avatar']}),
        ('Address', {'fields': ['address', 'city', 'state', 'zip_code']}),
        ('Location', {'fields': ['latitude', 'longitude']}),
        ('Permissions', {'fields': ['user_type', 'is_active', 'is_staff', 'is_superuser', 'is_verified', 'groups', 'user_permissions']}),
        ('Important dates', {'fields': ['last_login', 'date_joined']}),
    ]
    
    add_fieldsets = [
        (None, {
            'classes': ['wide'],
            'fields': ['email', 'password1', 'password2', 'user_type'],
        }),
    ]


@admin.register(UserActivityLog)
class UserActivityLogAdmin(admin.ModelAdmin):
    list_display = ['user', 'action', 'created_at', 'ip_address']
    list_filter = ['action', 'created_at']
    search_fields = ['user__email', 'description']
    ordering = ['-created_at']
    readonly_fields = ['user', 'action', 'description', 'ip_address', 'user_agent', 'created_at']
