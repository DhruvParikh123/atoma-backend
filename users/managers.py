from django.contrib.auth.base_user import BaseUserManager
from django.utils.translation import gettext_lazy as _


class UserManager(BaseUserManager):
    """Custom user manager for email-based authentication."""
    
    def create_user(self, email, password=None, **extra_fields):
        """Create and save a regular User with the given email and password."""
        if not email:
            raise ValueError(_('The Email must be set'))
        
        email = self.normalize_email(email)
        extra_fields.setdefault('is_active', True)
        
        user = self.model(email=email, **extra_fields)
        if password:
            user.set_password(password)
        user.save(using=self._db)
        return user
    
    def create_superuser(self, email, password=None, **extra_fields):
        """Create and save a SuperUser with the given email and password."""
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        extra_fields.setdefault('user_type', 'admin')
        
        if extra_fields.get('is_staff') is not True:
            raise ValueError(_('Superuser must have is_staff=True.'))
        if extra_fields.get('is_superuser') is not True:
            raise ValueError(_('Superuser must have is_superuser=True.'))
        
        return self.create_user(email, password, **extra_fields)
    
    def create_beautician(self, email, password=None, **extra_fields):
        """Create and save a Beautician user."""
        extra_fields.setdefault('user_type', 'beautician')
        return self.create_user(email, password, **extra_fields)
    
    def create_customer(self, email, password=None, **extra_fields):
        """Create and save a Customer user."""
        extra_fields.setdefault('user_type', 'customer')
        return self.create_user(email, password, **extra_fields)
