from django.urls import path
from .views import (
    ServiceCategoryListView,
    BeauticianListView,
    BeauticianDetailView,
    BeauticianProfileView,
    ServiceListCreateView,
    ServiceDetailView,
    AvailabilityListCreateView,
    AvailabilityDetailView,
    SpecialAvailabilityListCreateView,
    SpecialAvailabilityDetailView,
    PortfolioItemListCreateView,
    PortfolioItemDetailView,
    ReviewListCreateView,
    search_nearby_beauticians,
    beautician_dashboard
)

urlpatterns = [
    # Categories
    path('categories/', ServiceCategoryListView.as_view(), name='service-categories'),
    
    # Beauticians
    path('', BeauticianListView.as_view(), name='beautician-list'),
    path('search/', search_nearby_beauticians, name='beautician-search'),
    path('profile/', BeauticianProfileView.as_view(), name='beautician-profile'),
    path('dashboard/', beautician_dashboard, name='beautician-dashboard'),
    path('<int:pk>/', BeauticianDetailView.as_view(), name='beautician-detail'),
    
    # Services
    path('<int:beautician_id>/services/', ServiceListCreateView.as_view(), name='service-list'),
    path('services/', ServiceListCreateView.as_view(), name='my-services'),
    path('services/<int:pk>/', ServiceDetailView.as_view(), name='service-detail'),
    
    # Availability
    path('availability/', AvailabilityListCreateView.as_view(), name='availability-list'),
    path('availability/<int:pk>/', AvailabilityDetailView.as_view(), name='availability-detail'),
    
    # Special Availability
    path('special-availability/', SpecialAvailabilityListCreateView.as_view(), name='special-availability-list'),
    path('special-availability/<int:pk>/', SpecialAvailabilityDetailView.as_view(), name='special-availability-detail'),
    
    # Portfolio
    path('<int:beautician_id>/portfolio/', PortfolioItemListCreateView.as_view(), name='portfolio-list'),
    path('portfolio/', PortfolioItemListCreateView.as_view(), name='my-portfolio'),
    path('portfolio/<int:pk>/', PortfolioItemDetailView.as_view(), name='portfolio-detail'),
    
    # Reviews
    path('<int:beautician_id>/reviews/', ReviewListCreateView.as_view(), name='review-list'),
]
