import logging
from datetime import timedelta
from rest_framework import generics, permissions, status, filters
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from django.core.cache import cache

from .models import Booking, BookingStatusHistory, Payment
from .serializers import (
    BookingListSerializer,
    BookingDetailSerializer,
    BookingCreateSerializer,
    BookingUpdateSerializer,
    BookingStatusUpdateSerializer,
    BookingFilterSerializer,
    AssignNearestBeauticianSerializer,
    PaymentSerializer
)
from .filters import BookingFilter
from beauticians.models import Beautician, Service
from core.permissions import IsOwnerOrAdmin, IsBeauticianOwner, IsAdminUser
from core.utils import find_nearest_beautician, CacheKeyGenerator
from core.exceptions import BookingConflictError, BeauticianNotAvailableError

logger = logging.getLogger(__name__)


class BookingListCreateView(generics.ListCreateAPIView):
    """View for listing and creating bookings."""
    
    def get_serializer_class(self):
        if self.request.method == 'POST':
            return BookingCreateSerializer
        return BookingListSerializer
    
    def get_queryset(self):
        user = self.request.user
        
        if user.is_staff:
            return Booking.objects.all()
        
        # For beauticians, show their bookings
        try:
            beautician = user.beautician_profile
            return Booking.objects.filter(beautician=beautician)
        except Beautician.DoesNotExist:
            pass
        
        # For customers, show their bookings
        return Booking.objects.filter(customer=user)
    
    def get_permissions(self):
        return [permissions.IsAuthenticated()]
    
    def get_filter_backends(self):
        if self.request.method == 'GET':
            return [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
        return []
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Use transaction for atomic booking creation
        try:
            with transaction.atomic():
                # Select for update to prevent concurrent bookings
                beautician = Beautician.objects.select_for_update().get(
                    id=serializer.validated_data['beautician_id']
                )
                
                # Check if beautician is available
                if not beautician.is_available:
                    raise BeauticianNotAvailableError("Beautician is not currently available for bookings.")
                
                # Check for time conflicts
                service = Service.objects.get(id=serializer.validated_data['service_id'])
                booking_date = serializer.validated_data['booking_date']
                start_time = serializer.validated_data['start_time']
                
                # Calculate end time
                from datetime import datetime, timedelta as td
                start_dt = datetime.combine(booking_date, start_time)
                end_dt = start_dt + td(minutes=service.duration_minutes)
                end_time = end_dt.time()
                
                if Booking.check_time_conflict(
                    beautician.id, booking_date, start_time, end_time
                ):
                    raise BookingConflictError(
                        "This time slot is no longer available. Please select a different time."
                    )
                
                # Create the booking
                booking = serializer.save()
                
                logger.info(f"Booking created: {booking.id} by {request.user.email}")
                
                return Response({
                    'success': True,
                    'message': 'Booking created successfully',
                    'data': BookingDetailSerializer(booking).data
                }, status=status.HTTP_201_CREATED)
                
        except Beautician.DoesNotExist:
            return Response({
                'success': False,
                'error': {
                    'code': 'beautician_not_found',
                    'message': 'Beautician not found'
                }
            }, status=status.HTTP_404_NOT_FOUND)
        except Service.DoesNotExist:
            return Response({
                'success': False,
                'error': {
                    'code': 'service_not_found',
                    'message': 'Service not found'
                }
            }, status=status.HTTP_404_NOT_FOUND)


class BookingDetailView(generics.RetrieveUpdateDestroyAPIView):
    """View for retrieving, updating and deleting bookings."""
    queryset = Booking.objects.all()
    
    def get_serializer_class(self):
        if self.request.method in ['PUT', 'PATCH']:
            return BookingUpdateSerializer
        return BookingDetailSerializer
    
    def get_permissions(self):
        return [permissions.IsAuthenticated(), IsOwnerOrAdmin()]
    
    def get_object(self):
        obj = super().get_object()
        # Check ownership
        user = self.request.user
        try:
            beautician = user.beautician_profile
            if obj.beautician == beautician or obj.customer == user or user.is_staff:
                return obj
        except Beautician.DoesNotExist:
            if obj.customer == user or user.is_staff:
                return obj
        
        # Raise permission denied
        from rest_framework.exceptions import PermissionDenied
        raise PermissionDenied("You do not have permission to access this booking.")
    
    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        
        # Only allow updates for certain statuses
        if instance.status not in ['requested', 'accepted']:
            return Response({
                'success': False,
                'error': {
                    'code': 'cannot_update',
                    'message': f"Cannot update booking with status '{instance.status}'"
                }
            }, status=status.HTTP_400_BAD_REQUEST)
        
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        
        return Response({
            'success': True,
            'message': 'Booking updated successfully',
            'data': BookingDetailSerializer(instance).data
        })
    
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        
        # Soft delete - mark as cancelled
        if instance.status in ['requested', 'accepted']:
            instance.transition_to('cancelled', request.user)
            return Response({
                'success': True,
                'message': 'Booking cancelled successfully'
            })
        
        return Response({
            'success': False,
            'error': {
                'code': 'cannot_cancel',
                'message': f"Cannot cancel booking with status '{instance.status}'"
            }
        }, status=status.HTTP_400_BAD_REQUEST)


class BookingStatusUpdateView(generics.UpdateAPIView):
    """View for updating booking status."""
    queryset = Booking.objects.all()
    serializer_class = BookingStatusUpdateSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_object(self):
        obj = super().get_object()
        # Check permissions
        user = self.request.user
        try:
            beautician = user.beautician_profile
            if obj.beautician == beautician or obj.customer == user or user.is_staff:
                return obj
        except Beautician.DoesNotExist:
            if obj.customer == user or user.is_staff:
                return obj
        
        from rest_framework.exceptions import PermissionDenied
        raise PermissionDenied("You do not have permission to update this booking.")
    
    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        
        serializer = self.get_serializer(data=request.data, context={'booking': instance})
        serializer.is_valid(raise_exception=True)
        
        new_status = serializer.validated_data['status']
        
        try:
            with transaction.atomic():
                # Acquire lock for status update
                if not instance.acquire_lock(request.user):
                    return Response({
                        'success': False,
                        'error': {
                            'code': 'booking_locked',
                            'message': 'Booking is currently being processed. Please try again.'
                        }
                    }, status=status.HTTP_423_LOCKED)
                
                try:
                    # Update status
                    instance.transition_to(new_status, request.user)
                    
                    # Handle cancellation details
                    if new_status == 'cancelled':
                        instance.cancellation_reason = serializer.validated_data.get('cancellation_reason')
                        instance.cancellation_note = serializer.validated_data.get('cancellation_note', '')
                        instance.cancelled_by = request.user
                        instance.save(update_fields=['cancellation_reason', 'cancellation_note', 'cancelled_by'])
                    
                    logger.info(f"Booking {instance.id} status updated to {new_status} by {request.user.email}")
                    
                    return Response({
                        'success': True,
                        'message': f'Booking status updated to {new_status}',
                        'data': BookingDetailSerializer(instance).data
                    })
                    
                finally:
                    # Release lock
                    instance.release_lock()
                    
        except Exception as e:
            logger.error(f"Error updating booking status: {e}")
            return Response({
                'success': False,
                'error': {
                    'code': 'update_failed',
                    'message': str(e)
                }
            }, status=status.HTTP_400_BAD_REQUEST)


class PaymentCreateView(generics.CreateAPIView):
    """View for creating payments."""
    queryset = Payment.objects.all()
    serializer_class = PaymentSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def create(self, request, *args, **kwargs):
        booking_id = request.data.get('booking_id')
        
        try:
            booking = Booking.objects.get(id=booking_id, customer=request.user)
        except Booking.DoesNotExist:
            return Response({
                'success': False,
                'error': {
                    'code': 'booking_not_found',
                    'message': 'Booking not found or access denied'
                }
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Check if payment already exists
        if hasattr(booking, 'payment'):
            return Response({
                'success': False,
                'error': {
                    'code': 'payment_exists',
                    'message': 'Payment already exists for this booking'
                }
            }, status=status.HTTP_400_BAD_REQUEST)
        
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payment = serializer.save(booking=booking, amount=booking.total_amount)
        
        return Response({
            'success': True,
            'message': 'Payment initiated successfully',
            'data': PaymentSerializer(payment).data
        }, status=status.HTTP_201_CREATED)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def assign_nearest_beautician(request):
    """Create a booking and assign the nearest available beautician."""
    serializer = AssignNearestBeauticianSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    
    data = serializer.validated_data
    service = serializer.context['service']
    
    # Find available beauticians for this service
    available_beauticians = Beautician.objects.filter(
        services=service,
        is_verified=True,
        is_available=True,
        latitude__isnull=False,
        longitude__isnull=False
    ).distinct()
    
    if not available_beauticians.exists():
        return Response({
            'success': False,
            'error': {
                'code': 'no_beauticians_available',
                'message': 'No beauticians available for this service in your area'
            }
        }, status=status.HTTP_404_NOT_FOUND)
    
    # Calculate end time
    from datetime import datetime, timedelta
    start_dt = datetime.combine(data['booking_date'], data['start_time'])
    end_dt = start_dt + timedelta(minutes=service.duration_minutes)
    end_time = end_dt.time()
    
    # Find available beautician without time conflicts
    assigned_beautician = None
    distance = None
    
    with transaction.atomic():
        for beautician in available_beauticians.select_for_update():
            if not Booking.check_time_conflict(
                beautician.id, data['booking_date'], data['start_time'], end_time
            ):
                from core.utils import calculate_distance
                dist = calculate_distance(
                    float(data['customer_latitude']),
                    float(data['customer_longitude']),
                    float(beautician.latitude),
                    float(beautician.longitude)
                )
                
                if dist <= float(data['max_radius_km']):
                    assigned_beautician = beautician
                    distance = dist
                    break
    
    if not assigned_beautician:
        return Response({
            'success': False,
            'error': {
                'code': 'no_available_slots',
                'message': 'No beauticians available at the requested time within the specified radius'
            }
        }, status=status.HTTP_404_NOT_FOUND)
    
    # Create booking with assigned beautician
    booking = Booking.objects.create(
        customer=request.user,
        beautician=assigned_beautician,
        service=service,
        booking_date=data['booking_date'],
        start_time=data['start_time'],
        end_time=end_time,
        customer_address=data['customer_address'],
        customer_latitude=data['customer_latitude'],
        customer_longitude=data['customer_longitude'],
        service_price=service.price,
        total_amount=service.price,
        customer_notes=data.get('customer_notes', ''),
        status='requested'
    )
    
    logger.info(
        f"Auto-assigned booking created: {booking.id} - "
        f"Beautician: {assigned_beautician.id}, Distance: {distance:.2f}km"
    )
    
    return Response({
        'success': True,
        'message': f'Booking created and beautician assigned (Distance: {distance:.2f} km)',
        'data': BookingDetailSerializer(booking).data
    }, status=status.HTTP_201_CREATED)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated, IsAdminUser])
def admin_booking_list(request):
    """Admin view for listing all bookings with filters."""
    bookings = Booking.objects.all()
    
    # Apply filters
    status = request.query_params.get('status')
    date_from = request.query_params.get('date_from')
    date_to = request.query_params.get('date_to')
    beautician_id = request.query_params.get('beautician_id')
    customer_id = request.query_params.get('customer_id')
    
    if status:
        bookings = bookings.filter(status=status)
    if date_from:
        bookings = bookings.filter(booking_date__gte=date_from)
    if date_to:
        bookings = bookings.filter(booking_date__lte=date_to)
    if beautician_id:
        bookings = bookings.filter(beautician_id=beautician_id)
    if customer_id:
        bookings = bookings.filter(customer_id=customer_id)
    
    # Pagination
    from rest_framework.pagination import PageNumberPagination
    paginator = PageNumberPagination()
    paginator.page_size = 20
    result_page = paginator.paginate_queryset(bookings, request)
    
    serializer = BookingListSerializer(result_page, many=True)
    return paginator.get_paginated_response({
        'success': True,
        'data': serializer.data
    })


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def booking_calendar(request):
    """Get booking calendar for beautician or customer."""
    user = request.user
    month = request.query_params.get('month')
    year = request.query_params.get('year')
    
    try:
        month = int(month) if month else timezone.now().month
        year = int(year) if year else timezone.now().year
    except (ValueError, TypeError):
        return Response({
            'success': False,
            'error': {
                'code': 'invalid_date',
                'message': 'Invalid month or year'
            }
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Get bookings
    try:
        beautician = user.beautician_profile
        bookings = Booking.objects.filter(
            beautician=beautician,
            booking_date__month=month,
            booking_date__year=year
        ).exclude(status__in=['cancelled', 'rejected'])
    except Beautician.DoesNotExist:
        bookings = Booking.objects.filter(
            customer=user,
            booking_date__month=month,
            booking_date__year=year
        ).exclude(status__in=['cancelled', 'rejected'])
    
    serializer = BookingListSerializer(bookings, many=True)
    
    return Response({
        'success': True,
        'month': month,
        'year': year,
        'total_bookings': bookings.count(),
        'data': serializer.data
    })
