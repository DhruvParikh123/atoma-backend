import logging
from decimal import Decimal
from rest_framework import generics, permissions, status, filters
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django.db.models import Q, Min
from django_filters.rest_framework import DjangoFilterBackend
from django.core.cache import cache

from .models import Beautician, Service, ServiceCategory, Availability, SpecialAvailability, PortfolioItem, Review
from .serializers import (
    BeauticianListSerializer,
    BeauticianDetailSerializer,
    BeauticianCreateUpdateSerializer,
    ServiceSerializer,
    ServiceCategorySerializer,
    AvailabilitySerializer,
    SpecialAvailabilitySerializer,
    PortfolioItemSerializer,
    ReviewSerializer,
    BeauticianSearchSerializer
)
from .filters import BeauticianFilter
from core.permissions import IsBeauticianOwner, IsAdminUser
from core.utils import find_nearest_beautician, CacheKeyGenerator

logger = logging.getLogger(__name__)


class ServiceCategoryListView(generics.ListAPIView):
    """View for listing service categories."""
    queryset = ServiceCategory.objects.filter(is_active=True)
    serializer_class = ServiceCategorySerializer
    permission_classes = [permissions.AllowAny]


class BeauticianListView(generics.ListAPIView):
    """View for listing beauticians with filtering."""
    queryset = Beautician.objects.filter(is_verified=True, is_available=True)
    serializer_class = BeauticianListSerializer
    permission_classes = [permissions.AllowAny]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = BeauticianFilter
    search_fields = ['user__first_name', 'user__last_name', 'title', 'bio']
    ordering_fields = ['rating', 'experience_years', 'created_at']
    ordering = ['-rating']


class BeauticianDetailView(generics.RetrieveAPIView):
    """View for retrieving beautician details."""
    queryset = Beautician.objects.all()
    serializer_class = BeauticianDetailSerializer
    permission_classes = [permissions.AllowAny]
    lookup_field = 'pk'


class BeauticianProfileView(generics.RetrieveUpdateAPIView):
    """View for managing own beautician profile."""
    serializer_class = BeauticianDetailSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_object(self):
        return self.request.user.beautician_profile
    
    def get_serializer_class(self):
        if self.request.method in ['PUT', 'PATCH']:
            return BeauticianCreateUpdateSerializer
        return BeauticianDetailSerializer
    
    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        
        return Response({
            'success': True,
            'message': 'Profile updated successfully',
            'data': BeauticianDetailSerializer(instance).data
        })


class ServiceListCreateView(generics.ListCreateAPIView):
    """View for listing and creating services."""
    serializer_class = ServiceSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        beautician_id = self.kwargs.get('beautician_id')
        if beautician_id:
            return Service.objects.filter(beautician_id=beautician_id, is_active=True)
        return Service.objects.filter(beautician__user=self.request.user)
    
    def perform_create(self, serializer):
        beautician = self.request.user.beautician_profile
        serializer.save(beautician=beautician)


class ServiceDetailView(generics.RetrieveUpdateDestroyAPIView):
    """View for retrieving, updating and deleting services."""
    queryset = Service.objects.all()
    serializer_class = ServiceSerializer
    permission_classes = [permissions.IsAuthenticated, IsBeauticianOwner]
    
    def perform_destroy(self, instance):
        instance.is_active = False
        instance.save()


class AvailabilityListCreateView(generics.ListCreateAPIView):
    """View for listing and creating availability."""
    serializer_class = AvailabilitySerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return Availability.objects.filter(beautician__user=self.request.user)
    
    def perform_create(self, serializer):
        beautician = self.request.user.beautician_profile
        serializer.save(beautician=beautician)


class AvailabilityDetailView(generics.RetrieveUpdateDestroyAPIView):
    """View for managing availability."""
    queryset = Availability.objects.all()
    serializer_class = AvailabilitySerializer
    permission_classes = [permissions.IsAuthenticated, IsBeauticianOwner]


class SpecialAvailabilityListCreateView(generics.ListCreateAPIView):
    """View for managing special availability."""
    serializer_class = SpecialAvailabilitySerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return SpecialAvailability.objects.filter(beautician__user=self.request.user)
    
    def perform_create(self, serializer):
        beautician = self.request.user.beautician_profile
        serializer.save(beautician=beautician)


class SpecialAvailabilityDetailView(generics.RetrieveUpdateDestroyAPIView):
    """View for managing special availability."""
    queryset = SpecialAvailability.objects.all()
    serializer_class = SpecialAvailabilitySerializer
    permission_classes = [permissions.IsAuthenticated, IsBeauticianOwner]


class PortfolioItemListCreateView(generics.ListCreateAPIView):
    """View for listing and creating portfolio items."""
    serializer_class = PortfolioItemSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        beautician_id = self.kwargs.get('beautician_id')
        if beautician_id:
            return PortfolioItem.objects.filter(beautician_id=beautician_id)
        return PortfolioItem.objects.filter(beautician__user=self.request.user)
    
    def perform_create(self, serializer):
        beautician = self.request.user.beautician_profile
        serializer.save(beautician=beautician)


class PortfolioItemDetailView(generics.RetrieveUpdateDestroyAPIView):
    """View for managing portfolio items."""
    queryset = PortfolioItem.objects.all()
    serializer_class = PortfolioItemSerializer
    permission_classes = [permissions.IsAuthenticated, IsBeauticianOwner]


class ReviewListCreateView(generics.ListCreateAPIView):
    """View for listing and creating reviews."""
    serializer_class = ReviewSerializer
    
    def get_queryset(self):
        beautician_id = self.kwargs.get('beautician_id')
        if beautician_id:
            return Review.objects.filter(beautician_id=beautician_id, is_visible=True)
        return Review.objects.none()
    
    def get_permissions(self):
        if self.request.method == 'POST':
            return [permissions.IsAuthenticated()]
        return [permissions.AllowAny()]


@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def search_nearby_beauticians(request):
    """Search for nearby available beauticians."""
    serializer = BeauticianSearchSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    
    data = serializer.validated_data
    lat = float(data['latitude'])
    lon = float(data['longitude'])
    radius = float(data.get('radius_km', 10))
    
    # Get available beauticians
    beauticians = Beautician.objects.filter(
        is_verified=True,
        is_available=True,
        latitude__isnull=False,
        longitude__isnull=False
    )
    
    # Filter by service category if provided
    category_id = data.get('service_category')
    if category_id:
        beauticians = beauticians.filter(
            services__category_id=category_id,
            services__is_active=True
        ).distinct()
    
    # Filter by minimum rating
    min_rating = data.get('min_rating')
    if min_rating is not None:
        beauticians = beauticians.filter(rating__gte=min_rating)
    
    # Calculate distances and filter by radius
    results = []
    for beautician in beauticians:
        from core.utils import calculate_distance
        distance = calculate_distance(
            lat, lon,
            float(beautician.latitude),
            float(beautician.longitude)
        )
        
        if distance <= radius:
            beautician_data = BeauticianListSerializer(beautician).data
            beautician_data['distance_km'] = round(distance, 2)
            results.append(beautician_data)
    
    # Sort by distance
    results.sort(key=lambda x: x['distance_km'])
    
    return Response({
        'success': True,
        'count': len(results),
        'data': results
    })


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def beautician_dashboard(request):
    """Dashboard endpoint for beauticians."""
    try:
        beautician = request.user.beautician_profile
    except Beautician.DoesNotExist:
        return Response({
            'success': False,
            'error': {
                'code': 'not_beautician',
                'message': 'User is not a beautician'
            }
        }, status=status.HTTP_403_FORBIDDEN)
    
    # Get bookings stats
    bookings = beautician.bookings.all()
    
    data = {
        'beautician': BeauticianDetailSerializer(beautician).data,
        'stats': {
            'total_bookings': bookings.count(),
            'pending_bookings': bookings.filter(status='requested').count(),
            'upcoming_bookings': bookings.filter(status='accepted').count(),
            'completed_bookings': bookings.filter(status='completed').count(),
            'cancelled_bookings': bookings.filter(status='cancelled').count(),
            'total_services': beautician.services.filter(is_active=True).count(),
            'total_reviews': beautician.total_reviews,
            'average_rating': float(beautician.rating)
        }
    }
    
    return Response({
        'success': True,
        'data': data
    })
