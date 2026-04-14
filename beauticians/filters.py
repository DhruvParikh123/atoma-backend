import django_filters
from .models import Beautician


class BeauticianFilter(django_filters.FilterSet):
    """Filter set for beauticians."""
    
    city = django_filters.CharFilter(field_name='work_city', lookup_expr='iexact')
    state = django_filters.CharFilter(field_name='work_state', lookup_expr='iexact')
    min_experience = django_filters.NumberFilter(field_name='experience_years', lookup_expr='gte')
    max_experience = django_filters.NumberFilter(field_name='experience_years', lookup_expr='lte')
    min_rating = django_filters.NumberFilter(field_name='rating', lookup_expr='gte')
    service_category = django_filters.NumberFilter(
        field_name='services__category_id',
        distinct=True
    )
    
    class Meta:
        model = Beautician
        fields = [
            'city',
            'state',
            'min_experience',
            'max_experience',
            'min_rating',
            'is_available',
            'is_verified',
            'service_category'
        ]
