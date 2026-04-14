import django_filters
from .models import Booking


class BookingFilter(django_filters.FilterSet):
    """Filter set for bookings."""
    
    status = django_filters.ChoiceFilter(choices=Booking.STATUS_CHOICES)
    booking_date = django_filters.DateFilter()
    booking_date_from = django_filters.DateFilter(field_name='booking_date', lookup_expr='gte')
    booking_date_to = django_filters.DateFilter(field_name='booking_date', lookup_expr='lte')
    
    class Meta:
        model = Booking
        fields = [
            'status',
            'booking_date',
            'booking_date_from',
            'booking_date_to',
        ]
