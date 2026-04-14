from django.contrib import admin
from .models import Booking, BookingStatusHistory, Payment


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'customer', 'beautician', 'service', 'booking_date',
        'start_time', 'end_time', 'status', 'total_amount', 'requested_at'
    ]
    list_filter = [
        'status', 'booking_date', 'requested_at',
        'cancellation_reason'
    ]
    search_fields = [
        'customer__email', 'customer__first_name', 'customer__last_name',
        'beautician__user__email', 'service__name'
    ]
    ordering = ['-requested_at']
    readonly_fields = [
        'requested_at', 'accepted_at', 'started_at', 'completed_at',
        'cancelled_at', 'version', 'is_locked', 'locked_at', 'locked_by'
    ]
    
    fieldsets = [
        ('Booking Info', {
            'fields': [
                'customer', 'beautician', 'service', 'status',
                'booking_date', 'start_time', 'end_time'
            ]
        }),
        ('Location', {
            'fields': [
                'customer_address', 'customer_latitude', 'customer_longitude'
            ]
        }),
        ('Pricing', {
            'fields': ['service_price', 'total_amount']
        }),
        ('Timestamps', {
            'fields': [
                'requested_at', 'accepted_at', 'started_at',
                'completed_at', 'cancelled_at'
            ]
        }),
        ('Cancellation', {
            'fields': ['cancelled_by', 'cancellation_reason', 'cancellation_note']
        }),
        ('Notes', {
            'fields': ['customer_notes', 'beautician_notes']
        }),
        ('Lock Info', {
            'fields': ['is_locked', 'locked_at', 'locked_by', 'version'],
            'classes': ['collapse']
        }),
    ]


@admin.register(BookingStatusHistory)
class BookingStatusHistoryAdmin(admin.ModelAdmin):
    list_display = ['booking', 'from_status', 'to_status', 'changed_by', 'changed_at']
    list_filter = ['from_status', 'to_status', 'changed_at']
    search_fields = ['booking__id', 'changed_by__email']
    ordering = ['-changed_at']
    readonly_fields = ['booking', 'from_status', 'to_status', 'changed_by', 'changed_at']


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ['id', 'booking', 'amount', 'status', 'method', 'created_at', 'completed_at']
    list_filter = ['status', 'method', 'created_at']
    search_fields = ['booking__id', 'transaction_id']
    ordering = ['-created_at']
    readonly_fields = ['created_at', 'completed_at']
