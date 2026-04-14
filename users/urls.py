from django.urls import path
from .views import (
    UserRegistrationView,
    UserProfileView,
    ChangePasswordView,
    UserListView,
    UserActivityLogView,
    user_dashboard
)

urlpatterns = [
    path('register/', UserRegistrationView.as_view(), name='user-register'),
    path('profile/', UserProfileView.as_view(), name='user-profile'),
    path('change-password/', ChangePasswordView.as_view(), name='change-password'),
    path('list/', UserListView.as_view(), name='user-list'),
    path('activity-logs/', UserActivityLogView.as_view(), name='user-activity-logs'),
    path('activity-logs/<int:user_id>/', UserActivityLogView.as_view(), name='user-activity-logs-admin'),
    path('dashboard/', user_dashboard, name='user-dashboard'),
]
