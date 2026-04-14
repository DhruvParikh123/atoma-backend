import logging
from django.contrib.auth import get_user_model
from rest_framework import generics, permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken

from .models import UserActivityLog
from .serializers import (
    UserSerializer,
    UserRegistrationSerializer,
    UserLoginSerializer,
    UserUpdateSerializer,
    ChangePasswordSerializer,
    UserActivityLogSerializer
)
from core.permissions import IsOwnerOrAdmin

logger = logging.getLogger(__name__)
User = get_user_model()


class UserRegistrationView(generics.CreateAPIView):
    """View for user registration."""
    queryset = User.objects.all()
    serializer_class = UserRegistrationSerializer
    permission_classes = [permissions.AllowAny]
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        
        # Generate tokens
        refresh = RefreshToken.for_user(user)
        
        # Log activity
        UserActivityLog.objects.create(
            user=user,
            action='other',
            description='User registered successfully',
            ip_address=self.get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', '')
        )
        
        logger.info(f"New user registered: {user.email}")
        
        return Response({
            'success': True,
            'message': 'User registered successfully',
            'data': {
                'user': UserSerializer(user).data,
                'tokens': {
                    'access': str(refresh.access_token),
                    'refresh': str(refresh)
                }
            }
        }, status=status.HTTP_201_CREATED)
    
    def get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR')


class UserProfileView(generics.RetrieveUpdateAPIView):
    """View for retrieving and updating user profile."""
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_object(self):
        return self.request.user
    
    def get_serializer_class(self):
        if self.request.method in ['PUT', 'PATCH']:
            return UserUpdateSerializer
        return UserSerializer
    
    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        
        # Log activity
        UserActivityLog.objects.create(
            user=request.user,
            action='profile_update',
            description='Profile updated',
            ip_address=self.get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', '')
        )
        
        # Return updated user data using UserSerializer
        return Response({
            'success': True,
            'message': 'Profile updated successfully',
            'data': UserSerializer(instance).data
        })
    
    def get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR')


class ChangePasswordView(generics.UpdateAPIView):
    """View for changing password."""
    serializer_class = ChangePasswordSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_object(self):
        return self.request.user
    
    def update(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        user = self.get_object()
        user.set_password(serializer.validated_data['new_password'])
        user.save()
        
        # Log activity
        UserActivityLog.objects.create(
            user=request.user,
            action='password_change',
            description='Password changed',
            ip_address=self.get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', '')
        )
        
        logger.info(f"Password changed for user: {user.email}")
        
        return Response({
            'success': True,
            'message': 'Password changed successfully'
        })
    
    def get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR')


class UserListView(generics.ListAPIView):
    """View for listing all users (admin only)."""
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated, permissions.IsAdminUser]


class UserActivityLogView(generics.ListAPIView):
    """View for retrieving user activity logs."""
    serializer_class = UserActivityLogSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        user_id = self.kwargs.get('user_id')
        if user_id and self.request.user.is_staff:
            return UserActivityLog.objects.filter(user_id=user_id)
        return UserActivityLog.objects.filter(user=self.request.user)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def user_dashboard(request):
    """Dashboard endpoint for users."""
    user = request.user
    
    data = {
        'user': UserSerializer(user).data,
        'stats': {
            'total_bookings': 0,
            'upcoming_bookings': 0,
            'completed_bookings': 0
        }
    }
    
    # Add bookings stats if user has bookings
    if hasattr(user, 'bookings'):
        bookings = user.bookings.all()
        data['stats']['total_bookings'] = bookings.count()
        data['stats']['upcoming_bookings'] = bookings.filter(
            status__in=['accepted', 'in_progress']
        ).count()
        data['stats']['completed_bookings'] = bookings.filter(
            status='completed'
        ).count()
    
    return Response({
        'success': True,
        'data': data
    })
