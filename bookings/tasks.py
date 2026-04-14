import logging
from celery import shared_task
from django.utils import timezone
from datetime import timedelta

from .models import Booking
from users.models import UserActivityLog

logger = logging.getLogger(__name__)


@shared_task
def cleanup_expired_booking_locks():
    """Clean up expired booking locks (older than 5 minutes)."""
    expired_time = timezone.now() - timedelta(minutes=5)
    
    expired_bookings = Booking.objects.filter(
        is_locked=True,
        locked_at__lt=expired_time
    )
    
    count = 0
    for booking in expired_bookings:
        booking.release_lock()
        count += 1
    
    logger.info(f"Cleaned up {count} expired booking locks")
    return count


@shared_task
def send_booking_reminders():
    """Send reminders for upcoming bookings."""
    from datetime import date, time
    from django.core.mail import send_mail
    
    tomorrow = date.today() + timedelta(days=1)
    
    upcoming_bookings = Booking.objects.filter(
        booking_date=tomorrow,
        status='accepted'
    )
    
    for booking in upcoming_bookings:
        # Log the reminder
        logger.info(f"Sending reminder for booking {booking.id}")
        
        # Create activity log
        UserActivityLog.objects.create(
            user=booking.customer,
            action='other',
            description=f'Reminder sent for booking #{booking.id}'
        )
    
    return len(upcoming_bookings)


@shared_task
def auto_cancel_no_show_bookings():
    """Auto-cancel bookings where beautician or customer didn't show up."""
    from datetime import date, time, datetime
    
    # Find bookings that should have started but are still in 'accepted' status
    now = timezone.now()
    today = now.date()
    current_time = now.time()
    
    # Bookings that were supposed to start 30 minutes ago but still accepted
    time_threshold = (datetime.combine(today, current_time) - timedelta(minutes=30)).time()
    
    stale_bookings = Booking.objects.filter(
        booking_date__lte=today,
        start_time__lt=time_threshold,
        status='accepted'
    )
    
    count = 0
    for booking in stale_bookings:
        try:
            booking.transition_to('cancelled')
            booking.cancellation_reason = 'beautician_no_show' if booking.booking_date < today else 'other'
            booking.cancellation_note = 'Auto-cancelled due to no-show'
            booking.save()
            count += 1
            logger.info(f"Auto-cancelled booking {booking.id} due to no-show")
        except Exception as e:
            logger.error(f"Failed to auto-cancel booking {booking.id}: {e}")
    
    return count


@shared_task
def generate_daily_booking_report():
    """Generate daily booking statistics report."""
    from datetime import date, timedelta
    
    yesterday = date.today() - timedelta(days=1)
    
    stats = {
        'date': yesterday.isoformat(),
        'new_bookings': Booking.objects.filter(requested_at__date=yesterday).count(),
        'completed_bookings': Booking.objects.filter(completed_at__date=yesterday).count(),
        'cancelled_bookings': Booking.objects.filter(cancelled_at__date=yesterday).count(),
    }
    
    logger.info(f"Daily booking report for {yesterday}: {stats}")
    return stats
