from django.db import models, transaction
from django.core.validators import MinValueValidator
from django.utils import timezone
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)


class Booking(models.Model):
    """Booking model with lifecycle management."""
    
    STATUS_CHOICES = [
        ('requested', 'Requested'),
        ('accepted', 'Accepted'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('rejected', 'Rejected'),
    ]
    
    CANCELLATION_REASONS = [
        ('customer_request', 'Customer Request'),
        ('beautician_unavailable', 'Beautician Unavailable'),
        ('customer_no_show', 'Customer No Show'),
        ('beautician_no_show', 'Beautician No Show'),
        ('rescheduled', 'Rescheduled'),
        ('other', 'Other'),
    ]
    
    # Relationships
    customer = models.ForeignKey(
        'users.User',
        on_delete=models.PROTECT,
        related_name='bookings'
    )
    beautician = models.ForeignKey(
        'beauticians.Beautician',
        on_delete=models.PROTECT,
        related_name='bookings'
    )
    service = models.ForeignKey(
        'beauticians.Service',
        on_delete=models.PROTECT,
        related_name='bookings'
    )
    
    # Booking details
    booking_date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    
    # Customer location for mobile service
    customer_address = models.TextField()
    customer_latitude = models.DecimalField(
        max_digits=10, decimal_places=8,
        blank=True, null=True
    )
    customer_longitude = models.DecimalField(
        max_digits=11, decimal_places=8,
        blank=True, null=True
    )
    
    # Pricing
    service_price = models.DecimalField(
        max_digits=10, decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    total_amount = models.DecimalField(
        max_digits=10, decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    
    # Status
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='requested'
    )
    
    # Lifecycle timestamps
    requested_at = models.DateTimeField(auto_now_add=True)
    accepted_at = models.DateTimeField(blank=True, null=True)
    started_at = models.DateTimeField(blank=True, null=True)
    completed_at = models.DateTimeField(blank=True, null=True)
    cancelled_at = models.DateTimeField(blank=True, null=True)
    
    # Cancellation details
    cancelled_by = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        blank=True, null=True,
        related_name='cancelled_bookings'
    )
    cancellation_reason = models.CharField(
        max_length=50,
        choices=CANCELLATION_REASONS,
        blank=True
    )
    cancellation_note = models.TextField(blank=True)
    
    # Additional info
    customer_notes = models.TextField(blank=True)
    beautician_notes = models.TextField(blank=True)
    
    # Version for optimistic locking
    version = models.IntegerField(default=0)
    
    # Lock tracking for concurrent bookings
    is_locked = models.BooleanField(default=False)
    locked_at = models.DateTimeField(blank=True, null=True)
    locked_by = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        blank=True, null=True,
        related_name='locked_bookings'
    )
    
    class Meta:
        db_table = 'bookings'
        ordering = ['-requested_at']
        indexes = [
            models.Index(fields=['customer', 'status']),
            models.Index(fields=['beautician', 'status']),
            models.Index(fields=['booking_date', 'start_time']),
            models.Index(fields=['status']),
            models.Index(fields=['requested_at']),
        ]
        constraints = [
            models.CheckConstraint(
                check=models.Q(start_time__lt=models.F('end_time')),
                name='start_before_end'
            ),
        ]
    
    def __str__(self):
        return f"Booking #{self.id} - {self.customer.get_full_name()} with {self.beautician}"
    
    def save(self, *args, **kwargs):
        if not self.end_time and self.service:
            from datetime import datetime, timedelta
            start_dt = datetime.combine(self.booking_date, self.start_time)
            end_dt = start_dt + timedelta(minutes=self.service.duration_minutes)
            self.end_time = end_dt.time()
        
        if not self.total_amount:
            self.total_amount = self.service_price
        
        super().save(*args, **kwargs)
    
    def can_transition_to(self, new_status):
        """Check if status transition is valid."""
        valid_transitions = {
            'requested': ['accepted', 'rejected', 'cancelled'],
            'accepted': ['in_progress', 'cancelled'],
            'in_progress': ['completed', 'cancelled'],
            'completed': [],
            'cancelled': [],
            'rejected': [],
        }
        return new_status in valid_transitions.get(self.status, [])
    
    def transition_to(self, new_status, user=None):
        """Transition booking to new status with validation."""
        from core.exceptions import InvalidBookingStatusError
        
        if not self.can_transition_to(new_status):
            raise InvalidBookingStatusError(
                f"Cannot transition from '{self.status}' to '{new_status}'"
            )
        
        old_status = self.status
        self.status = new_status
        
        # Update timestamps based on status
        now = timezone.now()
        if new_status == 'accepted':
            self.accepted_at = now
        elif new_status == 'in_progress':
            self.started_at = now
        elif new_status == 'completed':
            self.completed_at = now
        elif new_status == 'cancelled':
            self.cancelled_at = now
            if user:
                self.cancelled_by = user
        
        self.save(update_fields=[
            'status', 'accepted_at', 'started_at', 
            'completed_at', 'cancelled_at', 'cancelled_by', 'version'
        ])
        
        # Log the transition
        BookingStatusHistory.objects.create(
            booking=self,
            from_status=old_status,
            to_status=new_status,
            changed_by=user
        )
        
        logger.info(f"Booking {self.id} transitioned from {old_status} to {new_status}")
        
        return self
    
    def acquire_lock(self, user):
        """Acquire lock for concurrent booking operations."""
        if self.is_locked and self.locked_at:
            # Check if lock is stale (older than 5 minutes)
            from datetime import timedelta
            if timezone.now() - self.locked_at > timedelta(minutes=5):
                # Release stale lock
                self.release_lock()
            else:
                return False
        
        self.is_locked = True
        self.locked_at = timezone.now()
        self.locked_by = user
        self.save(update_fields=['is_locked', 'locked_at', 'locked_by'])
        return True
    
    def release_lock(self):
        """Release the booking lock."""
        self.is_locked = False
        self.locked_at = None
        self.locked_by = None
        self.save(update_fields=['is_locked', 'locked_at', 'locked_by'])
    
    @classmethod
    def check_time_conflict(cls, beautician_id, booking_date, start_time, end_time, exclude_booking_id=None):
        """Check if there's a time conflict for a beautician."""
        from django.db.models import Q
        
        queryset = cls.objects.filter(
            beautician_id=beautician_id,
            booking_date=booking_date,
            status__in=['requested', 'accepted', 'in_progress']
        ).exclude(
            models.Q(end_time__lte=start_time) | models.Q(start_time__gte=end_time)
        )
        
        if exclude_booking_id:
            queryset = queryset.exclude(id=exclude_booking_id)
        
        return queryset.exists()


class BookingStatusHistory(models.Model):
    """History of booking status changes."""
    
    booking = models.ForeignKey(
        Booking,
        on_delete=models.CASCADE,
        related_name='status_history'
    )
    from_status = models.CharField(max_length=20)
    to_status = models.CharField(max_length=20)
    changed_by = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        blank=True, null=True
    )
    changed_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True)
    
    class Meta:
        db_table = 'booking_status_history'
        ordering = ['-changed_at']
        indexes = [
            models.Index(fields=['booking', 'changed_at']),
        ]
    
    def __str__(self):
        return f"Booking {self.booking_id}: {self.from_status} -> {self.to_status}"


class Payment(models.Model):
    """Payment model for bookings."""
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
        ('partially_refunded', 'Partially Refunded'),
    ]
    
    METHOD_CHOICES = [
        ('credit_card', 'Credit Card'),
        ('debit_card', 'Debit Card'),
        ('upi', 'UPI'),
        ('cash', 'Cash'),
        ('wallet', 'Wallet'),
    ]
    
    booking = models.OneToOneField(
        Booking,
        on_delete=models.CASCADE,
        related_name='payment'
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    method = models.CharField(max_length=20, choices=METHOD_CHOICES)
    transaction_id = models.CharField(max_length=255, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(blank=True, null=True)
    
    class Meta:
        db_table = 'payments'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Payment for Booking #{self.booking_id} - {self.status}"
