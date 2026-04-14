from django.contrib import admin
from .models import Beautician, Service, ServiceCategory, Availability, SpecialAvailability, PortfolioItem, Review


@admin.register(Beautician)
class BeauticianAdmin(admin.ModelAdmin):
    list_display = ['user', 'title', 'experience_years', 'is_available', 'is_verified', 'rating', 'created_at']
    list_filter = ['is_available', 'is_verified', 'experience_years', 'created_at']
    search_fields = ['user__email', 'user__first_name', 'user__last_name', 'title', 'license_number']
    ordering = ['-created_at']
    
    fieldsets = [
        (None, {'fields': ['user']}),
        ('Professional Info', {'fields': ['title', 'bio', 'experience_years', 'license_number']}),
        ('Work Location', {'fields': ['work_address', 'work_city', 'work_state', 'work_zip_code', 'service_radius_km']}),
        ('Coordinates', {'fields': ['latitude', 'longitude']}),
        ('Status', {'fields': ['is_available', 'is_verified', 'rating', 'total_reviews']}),
    ]


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ['name', 'beautician', 'category', 'price', 'duration_minutes', 'is_active']
    list_filter = ['is_active', 'category', 'created_at']
    search_fields = ['name', 'description', 'beautician__user__email']
    ordering = ['-created_at']


@admin.register(ServiceCategory)
class ServiceCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'is_active']
    list_filter = ['is_active']
    search_fields = ['name', 'description']


@admin.register(Availability)
class AvailabilityAdmin(admin.ModelAdmin):
    list_display = ['beautician', 'get_day_of_week_display', 'start_time', 'end_time', 'is_available']
    list_filter = ['day_of_week', 'is_available']
    search_fields = ['beautician__user__email']


@admin.register(SpecialAvailability)
class SpecialAvailabilityAdmin(admin.ModelAdmin):
    list_display = ['beautician', 'date', 'type', 'start_time', 'end_time']
    list_filter = ['type', 'date']
    search_fields = ['beautician__user__email']
    ordering = ['-date']


@admin.register(PortfolioItem)
class PortfolioItemAdmin(admin.ModelAdmin):
    list_display = ['beautician', 'title', 'created_at']
    search_fields = ['beautician__user__email', 'title']
    ordering = ['-created_at']


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ['beautician', 'customer', 'booking', 'rating', 'is_visible', 'created_at']
    list_filter = ['rating', 'is_visible', 'created_at']
    search_fields = ['beautician__user__email', 'customer__email', 'comment']
    ordering = ['-created_at']
