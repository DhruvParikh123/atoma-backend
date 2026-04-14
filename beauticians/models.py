from django.db import models, transaction
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db.models import Q


class Beautician(models.Model):
    """Beautician profile model."""
    
    user = models.OneToOneField(
        'users.User', 
        on_delete=models.CASCADE, 
        related_name='beautician_profile'
    )
    
    # Professional details
    title = models.CharField(max_length=200, blank=True)
    bio = models.TextField(blank=True)
    experience_years = models.PositiveIntegerField(default=0)
    license_number = models.CharField(max_length=100, blank=True, unique=True)
    
    # Work location
    work_address = models.TextField(blank=True)
    work_city = models.CharField(max_length=100, blank=True)
    work_state = models.CharField(max_length=100, blank=True)
    work_zip_code = models.CharField(max_length=20, blank=True)
    
    # Service area (for mobile beauticians)
    service_radius_km = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        default=10.00,
        validators=[MinValueValidator(0), MaxValueValidator(500)]
    )
    
    # Location (for finding nearest beautician)
    latitude = models.DecimalField(
        max_digits=10, 
        decimal_places=8, 
        blank=True, 
        null=True,
        validators=[MinValueValidator(-90), MaxValueValidator(90)]
    )
    longitude = models.DecimalField(
        max_digits=11, 
        decimal_places=8, 
        blank=True, 
        null=True,
        validators=[MinValueValidator(-180), MaxValueValidator(180)]
    )
    
    # Status
    is_available = models.BooleanField(default=True)
    is_verified = models.BooleanField(default=False)
    rating = models.DecimalField(
        max_digits=3, 
        decimal_places=2, 
        default=0.00,
        validators=[MinValueValidator(0), MaxValueValidator(5)]
    )
    total_reviews = models.PositiveIntegerField(default=0)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'beauticians'
        ordering = ['-rating', '-created_at']
        indexes = [
            models.Index(fields=['is_available', 'is_verified']),
            models.Index(fields=['latitude', 'longitude']),
            models.Index(fields=['rating']),
        ]
    
    def __str__(self):
        return f"{self.user.get_full_name()} - {self.title or 'Beautician'}"
    
    def update_rating(self, new_rating):
        """Update the average rating when a new review is added."""
        current_total = self.rating * self.total_reviews
        self.total_reviews += 1
        self.rating = (current_total + new_rating) / self.total_reviews
        self.save(update_fields=['rating', 'total_reviews'])


class ServiceCategory(models.Model):
    """Service category model."""
    
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    icon = models.ImageField(upload_to='service_icons/', blank=True, null=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        db_table = 'service_categories'
        verbose_name_plural = 'service categories'
        ordering = ['name']
    
    def __str__(self):
        return self.name


class Service(models.Model):
    """Service offered by a beautician."""
    
    beautician = models.ForeignKey(
        Beautician, 
        on_delete=models.CASCADE, 
        related_name='services'
    )
    category = models.ForeignKey(
        ServiceCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='services'
    )
    
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    price = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        validators=[MinValueValidator(0)]
    )
    duration_minutes = models.PositiveIntegerField(
        validators=[MinValueValidator(5)],
        help_text="Duration of the service in minutes"
    )
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'services'
        ordering = ['-is_active', 'name']
        unique_together = ['beautician', 'name']
        indexes = [
            models.Index(fields=['beautician', 'is_active']),
            models.Index(fields=['category']),
        ]
    
    def __str__(self):
        return f"{self.name} - {self.beautician}"


class Availability(models.Model):
    """Beautician availability schedule."""
    
    DAY_CHOICES = [
        (0, 'Monday'),
        (1, 'Tuesday'),
        (2, 'Wednesday'),
        (3, 'Thursday'),
        (4, 'Friday'),
        (5, 'Saturday'),
        (6, 'Sunday'),
    ]
    
    beautician = models.ForeignKey(
        Beautician,
        on_delete=models.CASCADE,
        related_name='availability'
    )
    day_of_week = models.IntegerField(choices=DAY_CHOICES)
    start_time = models.TimeField()
    end_time = models.TimeField()
    is_available = models.BooleanField(default=True)
    
    class Meta:
        db_table = 'availability'
        verbose_name_plural = 'availabilities'
        unique_together = ['beautician', 'day_of_week']
        ordering = ['day_of_week', 'start_time']
    
    def __str__(self):
        return f"{self.beautician} - {self.get_day_of_week_display()}"
    
    def clean(self):
        from django.core.exceptions import ValidationError
        if self.start_time >= self.end_time:
            raise ValidationError("End time must be after start time.")


class SpecialAvailability(models.Model):
    """Special availability overrides (for holidays, time off, etc.)."""
    
    TYPE_CHOICES = [
        ('available', 'Available'),
        ('unavailable', 'Unavailable'),
    ]
    
    beautician = models.ForeignKey(
        Beautician,
        on_delete=models.CASCADE,
        related_name='special_availability'
    )
    date = models.DateField()
    type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='unavailable')
    start_time = models.TimeField(blank=True, null=True)
    end_time = models.TimeField(blank=True, null=True)
    reason = models.CharField(max_length=200, blank=True)
    
    class Meta:
        db_table = 'special_availability'
        unique_together = ['beautician', 'date']
        ordering = ['-date']
    
    def __str__(self):
        return f"{self.beautician} - {self.date} ({self.type})"


class PortfolioItem(models.Model):
    """Portfolio items for beauticians (photos of work)."""
    
    beautician = models.ForeignKey(
        Beautician,
        on_delete=models.CASCADE,
        related_name='portfolio_items'
    )
    image = models.ImageField(upload_to='portfolio/')
    title = models.CharField(max_length=200, blank=True)
    description = models.TextField(blank=True)
    service = models.ForeignKey(
        Service,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='portfolio_items'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'portfolio_items'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.beautician} - {self.title or 'Portfolio Item'}"


class Review(models.Model):
    """Customer reviews for beauticians."""
    
    beautician = models.ForeignKey(
        Beautician,
        on_delete=models.CASCADE,
        related_name='reviews'
    )
    customer = models.ForeignKey(
        'users.User',
        on_delete=models.CASCADE,
        related_name='reviews_given'
    )
    booking = models.OneToOneField(
        'bookings.Booking',
        on_delete=models.CASCADE,
        related_name='review'
    )
    rating = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    comment = models.TextField(blank=True)
    is_visible = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'reviews'
        unique_together = ['customer', 'booking']
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.customer} rated {self.beautician} - {self.rating} stars"
    
    def save(self, *args, **kwargs):
        is_new = self.pk is None
        super().save(*args, **kwargs)
        if is_new:
            # Update beautician's rating
            self.beautician.update_rating(self.rating)
