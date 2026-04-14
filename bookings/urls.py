from django.urls import path
from .views import (
    BookingListCreateView,
    BookingDetailView,
    BookingStatusUpdateView,
    PaymentCreateView,
    assign_nearest_beautician,
    admin_booking_list,
    booking_calendar
)

urlpatterns = [
    # Booking CRUD
    path('', BookingListCreateView.as_view(), name='booking-list'),
    path('<int:pk>/', BookingDetailView.as_view(), name='booking-detail'),
    path('<int:pk>/status/', BookingStatusUpdateView.as_view(), name='booking-status-update'),
    
    # Auto-assign beautician
    path('assign-nearest/', assign_nearest_beautician, name='assign-nearest-beautician'),
    
    # Payments
    path('payments/', PaymentCreateView.as_view(), name='payment-create'),
    
    # Admin
    path('admin/list/', admin_booking_list, name='admin-booking-list'),
    
    # Calendar
    path('calendar/', booking_calendar, name='booking-calendar'),
]
