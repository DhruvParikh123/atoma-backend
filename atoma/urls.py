from django.contrib import admin
from django.urls import path, include
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenBlacklistView,
)
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from rest_framework import permissions

schema_view = get_schema_view(
    openapi.Info(
        title="Atoma API",
        default_version='v1',
        description="Beautician Booking Platform API",
        terms_of_service="https://www.atoma.com/terms/",
        contact=openapi.Contact(email="contact@atoma.com"),
        license=openapi.License(name="BSD License"),
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/auth/login/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/auth/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/auth/logout/', TokenBlacklistView.as_view(), name='token_blacklist'),
    path('api/users/', include('users.urls')),
    path('api/beauticians/', include('beauticians.urls')),
    path('api/bookings/', include('bookings.urls')),
]

# Add Swagger and ReDoc URLs
try:
    urlpatterns += [
        path('api/docs/', schema_view.with_ui('swagger', cache_timeout=0), name='swagger-ui'),
        path('api/redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='redoc-ui'),
    ]
except ImportError:
    pass
