from rest_framework import serializers
from .models import Beautician, Service, ServiceCategory, Availability, SpecialAvailability, PortfolioItem, Review
from users.serializers import UserSerializer


class ServiceCategorySerializer(serializers.ModelSerializer):
    """Serializer for service categories."""
    
    class Meta:
        model = ServiceCategory
        fields = ['id', 'name', 'description', 'icon', 'is_active']


class ServiceSerializer(serializers.ModelSerializer):
    """Serializer for services."""
    
    category_name = serializers.CharField(source='category.name', read_only=True)
    duration_formatted = serializers.SerializerMethodField()
    
    class Meta:
        model = Service
        fields = [
            'id', 'beautician', 'category', 'category_name', 'name',
            'description', 'price', 'duration_minutes', 'duration_formatted',
            'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['beautician']
    
    def get_duration_formatted(self, obj):
        hours = obj.duration_minutes // 60
        minutes = obj.duration_minutes % 60
        if hours > 0:
            return f"{hours}h {minutes}m" if minutes > 0 else f"{hours}h"
        return f"{minutes}m"


class AvailabilitySerializer(serializers.ModelSerializer):
    """Serializer for availability."""
    
    day_name = serializers.CharField(source='get_day_of_week_display', read_only=True)
    
    class Meta:
        model = Availability
        fields = ['id', 'beautician', 'day_of_week', 'day_name', 'start_time', 'end_time', 'is_available']
        read_only_fields = ['beautician']


class SpecialAvailabilitySerializer(serializers.ModelSerializer):
    """Serializer for special availability."""
    
    class Meta:
        model = SpecialAvailability
        fields = ['id', 'beautician', 'date', 'type', 'start_time', 'end_time', 'reason']
        read_only_fields = ['beautician']


class PortfolioItemSerializer(serializers.ModelSerializer):
    """Serializer for portfolio items."""
    
    class Meta:
        model = PortfolioItem
        fields = ['id', 'beautician', 'image', 'title', 'description', 'service', 'created_at']
        read_only_fields = ['beautician']


class ReviewSerializer(serializers.ModelSerializer):
    """Serializer for reviews."""
    
    customer_name = serializers.CharField(source='customer.get_full_name', read_only=True)
    
    class Meta:
        model = Review
        fields = [
            'id', 'beautician', 'customer', 'customer_name', 'booking',
            'rating', 'comment', 'is_visible', 'created_at'
        ]
        read_only_fields = ['beautician', 'customer', 'booking']


class BeauticianListSerializer(serializers.ModelSerializer):
    """Serializer for listing beauticians."""
    
    user = UserSerializer(read_only=True)
    services_count = serializers.IntegerField(source='services.filter(is_active=True).count', read_only=True)
    min_price = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    
    class Meta:
        model = Beautician
        fields = [
            'id', 'user', 'title', 'bio', 'experience_years',
            'work_city', 'work_state', 'latitude', 'longitude',
            'service_radius_km', 'is_available', 'is_verified',
            'rating', 'total_reviews', 'services_count', 'min_price',
            'created_at'
        ]


class BeauticianDetailSerializer(serializers.ModelSerializer):
    """Serializer for detailed beautician profile."""
    
    user = UserSerializer(read_only=True)
    services = ServiceSerializer(many=True, read_only=True)
    availability = AvailabilitySerializer(many=True, read_only=True)
    portfolio_items = PortfolioItemSerializer(many=True, read_only=True)
    reviews = ReviewSerializer(many=True, read_only=True)
    
    class Meta:
        model = Beautician
        fields = [
            'id', 'user', 'title', 'bio', 'experience_years', 'license_number',
            'work_address', 'work_city', 'work_state', 'work_zip_code',
            'service_radius_km', 'latitude', 'longitude',
            'is_available', 'is_verified', 'rating', 'total_reviews',
            'services', 'availability', 'portfolio_items', 'reviews',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['user', 'rating', 'total_reviews']


class BeauticianCreateUpdateSerializer(serializers.ModelSerializer):
    """Serializer for creating and updating beautician profile."""
    
    class Meta:
        model = Beautician
        fields = [
            'title', 'bio', 'experience_years', 'license_number',
            'work_address', 'work_city', 'work_state', 'work_zip_code',
            'service_radius_km', 'latitude', 'longitude', 'is_available'
        ]
    
    def validate_latitude(self, value):
        if value is not None and not (-90 <= value <= 90):
            raise serializers.ValidationError("Latitude must be between -90 and 90.")
        return value
    
    def validate_longitude(self, value):
        if value is not None and not (-180 <= value <= 180):
            raise serializers.ValidationError("Longitude must be between -180 and 180.")
        return value


class BeauticianSearchSerializer(serializers.Serializer):
    """Serializer for searching beauticians."""
    
    latitude = serializers.DecimalField(max_digits=10, decimal_places=8, required=True)
    longitude = serializers.DecimalField(max_digits=11, decimal_places=8, required=True)
    radius_km = serializers.DecimalField(max_digits=5, decimal_places=2, required=False, default=10.00)
    service_category = serializers.IntegerField(required=False)
    min_rating = serializers.DecimalField(max_digits=3, decimal_places=2, required=False, min_value=0, max_value=5)
