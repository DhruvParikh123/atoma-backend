from rest_framework import serializers
from django.db import transaction
from django.utils import timezone
from .models import Booking, BookingStatusHistory, Payment
from beauticians.models import Beautician, Service
from users.models import User


class PaymentSerializer(serializers.ModelSerializer):
    """Serializer for payments."""
    
    class Meta:
        model = Payment
        fields = [
            'id', 'booking', 'amount', 'status', 'method',
            'transaction_id', 'created_at', 'completed_at'
        ]
        read_only_fields = ['booking', 'created_at', 'completed_at']


class BookingStatusHistorySerializer(serializers.ModelSerializer):
    """Serializer for booking status history."""
    
    changed_by_name = serializers.CharField(source='changed_by.get_full_name', read_only=True)
    
    class Meta:
        model = BookingStatusHistory
        fields = ['id', 'from_status', 'to_status', 'changed_by_name', 'changed_at', 'notes']


class BookingListSerializer(serializers.ModelSerializer):
    """Serializer for listing bookings."""
    
    customer_name = serializers.CharField(source='customer.get_full_name', read_only=True)
    beautician_name = serializers.CharField(source='beautician.user.get_full_name', read_only=True)
    service_name = serializers.CharField(source='service.name', read_only=True)
    duration_minutes = serializers.IntegerField(source='service.duration_minutes', read_only=True)
    payment_status = serializers.CharField(source='payment.status', read_only=True, default=None)
    
    class Meta:
        model = Booking
        fields = [
            'id', 'customer_name', 'beautician_name', 'service_name',
            'booking_date', 'start_time', 'end_time', 'duration_minutes',
            'status', 'total_amount', 'payment_status',
            'requested_at', 'customer_address'
        ]


class BookingDetailSerializer(serializers.ModelSerializer):
    """Serializer for detailed booking information."""
    
    customer = serializers.SerializerMethodField()
    beautician = serializers.SerializerMethodField()
    service = serializers.SerializerMethodField()
    status_history = BookingStatusHistorySerializer(many=True, read_only=True)
    payment = PaymentSerializer(read_only=True)
    duration_minutes = serializers.IntegerField(source='service.duration_minutes', read_only=True)
    
    class Meta:
        model = Booking
        fields = [
            'id', 'customer', 'beautician', 'service',
            'booking_date', 'start_time', 'end_time', 'duration_minutes',
            'customer_address', 'customer_latitude', 'customer_longitude',
            'service_price', 'total_amount',
            'status', 'requested_at', 'accepted_at', 'started_at', 'completed_at',
            'cancelled_at', 'cancellation_reason', 'cancellation_note',
            'customer_notes', 'beautician_notes',
            'status_history', 'payment'
        ]
    
    def get_customer(self, obj):
        return {
            'id': obj.customer.id,
            'name': obj.customer.get_full_name(),
            'email': obj.customer.email,
            'phone': obj.customer.phone,
            'address': obj.customer.address,
        }
    
    def get_beautician(self, obj):
        return {
            'id': obj.beautician.id,
            'name': obj.beautician.user.get_full_name(),
            'email': obj.beautician.user.email,
            'phone': obj.beautician.user.phone,
            'title': obj.beautician.title,
        }
    
    def get_service(self, obj):
        return {
            'id': obj.service.id,
            'name': obj.service.name,
            'description': obj.service.description,
            'duration_minutes': obj.service.duration_minutes,
        }


class BookingCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating bookings."""
    
    beautician_id = serializers.IntegerField(write_only=True)
    service_id = serializers.IntegerField(write_only=True)
    customer_notes = serializers.CharField(required=False, allow_blank=True)
    
    class Meta:
        model = Booking
        fields = [
            'beautician_id', 'service_id', 'booking_date', 'start_time',
            'customer_address', 'customer_latitude', 'customer_longitude',
            'customer_notes'
        ]
    
    def validate(self, data):
        # Validate beautician exists and is available
        try:
            beautician = Beautician.objects.get(
                id=data['beautician_id'],
                is_verified=True,
                is_available=True
            )
        except Beautician.DoesNotExist:
            raise serializers.ValidationError(
                {"beautician_id": "Beautician not found or not available."}
            )
        
        # Validate service exists and belongs to the beautician
        try:
            service = Service.objects.get(
                id=data['service_id'],
                beautician=beautician,
                is_active=True
            )
        except Service.DoesNotExist:
            raise serializers.ValidationError(
                {"service_id": "Service not found or not available for this beautician."}
            )
        
        # Validate booking date is not in the past
        from datetime import date
        if data['booking_date'] < date.today():
            raise serializers.ValidationError(
                {"booking_date": "Booking date cannot be in the past."}
            )
        
        # Validate coordinates
        lat = data.get('customer_latitude')
        lon = data.get('customer_longitude')
        if lat is not None and lon is not None:
            if not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
                raise serializers.ValidationError(
                    {"coordinates": "Invalid coordinates."}
                )
        
        # Store validated objects for use in create
        self.context['beautician'] = beautician
        self.context['service'] = service
        
        return data
    
    def create(self, validated_data):
        beautician = self.context['beautician']
        service = self.context['service']
        customer = self.context['request'].user
        
        # Calculate end time
        from datetime import datetime, timedelta
        start_dt = datetime.combine(validated_data['booking_date'], validated_data['start_time'])
        end_dt = start_dt + timedelta(minutes=service.duration_minutes)
        
        # Create booking
        booking = Booking.objects.create(
            customer=customer,
            beautician=beautician,
            service=service,
            booking_date=validated_data['booking_date'],
            start_time=validated_data['start_time'],
            end_time=end_dt.time(),
            customer_address=validated_data.get('customer_address', ''),
            customer_latitude=validated_data.get('customer_latitude'),
            customer_longitude=validated_data.get('customer_longitude'),
            service_price=service.price,
            total_amount=service.price,
            customer_notes=validated_data.get('customer_notes', ''),
            status='requested'
        )
        
        return booking


class BookingUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating booking details."""
    
    class Meta:
        model = Booking
        fields = ['customer_notes', 'customer_address', 'customer_latitude', 'customer_longitude']


class BookingStatusUpdateSerializer(serializers.Serializer):
    """Serializer for updating booking status."""
    
    status = serializers.ChoiceField(choices=Booking.STATUS_CHOICES)
    cancellation_reason = serializers.ChoiceField(
        choices=Booking.CANCELLATION_REASONS,
        required=False,
        allow_blank=True
    )
    cancellation_note = serializers.CharField(required=False, allow_blank=True)
    notes = serializers.CharField(required=False, allow_blank=True)
    
    def validate(self, data):
        booking = self.context['booking']
        new_status = data['status']
        
        if not booking.can_transition_to(new_status):
            raise serializers.ValidationError(
                {"status": f"Cannot transition from '{booking.status}' to '{new_status}'"}
            )
        
        # Validate cancellation reason if status is cancelled
        if new_status == 'cancelled' and not data.get('cancellation_reason'):
            raise serializers.ValidationError(
                {"cancellation_reason": "Cancellation reason is required when cancelling a booking."}
            )
        
        return data


class BookingFilterSerializer(serializers.Serializer):
    """Serializer for filtering bookings."""
    
    status = serializers.ChoiceField(choices=Booking.STATUS_CHOICES, required=False)
    date_from = serializers.DateField(required=False)
    date_to = serializers.DateField(required=False)
    beautician_id = serializers.IntegerField(required=False)
    customer_id = serializers.IntegerField(required=False)


class AssignNearestBeauticianSerializer(serializers.Serializer):
    """Serializer for assigning nearest beautician."""
    
    service_id = serializers.IntegerField(required=True)
    booking_date = serializers.DateField(required=True)
    start_time = serializers.TimeField(required=True)
    customer_address = serializers.CharField(required=True)
    customer_latitude = serializers.DecimalField(max_digits=10, decimal_places=8, required=True)
    customer_longitude = serializers.DecimalField(max_digits=11, decimal_places=8, required=True)
    max_radius_km = serializers.DecimalField(max_digits=5, decimal_places=2, required=False, default=10.00)
    customer_notes = serializers.CharField(required=False, allow_blank=True)
    
    def validate(self, data):
        from datetime import date
        if data['booking_date'] < date.today():
            raise serializers.ValidationError(
                {"booking_date": "Booking date cannot be in the past."}
            )
        
        # Validate coordinates
        if not (-90 <= data['customer_latitude'] <= 90):
            raise serializers.ValidationError(
                {"customer_latitude": "Latitude must be between -90 and 90."}
            )
        if not (-180 <= data['customer_longitude'] <= 180):
            raise serializers.ValidationError(
                {"customer_longitude": "Longitude must be between -180 and 180."}
            )
        
        # Validate service exists
        try:
            service = Service.objects.get(
                id=data['service_id'],
                is_active=True
            )
            self.context['service'] = service
        except Service.DoesNotExist:
            raise serializers.ValidationError(
                {"service_id": "Service not found or not available."}
            )
        
        return data
