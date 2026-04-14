import math
from typing import Tuple, Optional
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)


def calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate the Haversine distance between two points on Earth.
    Returns distance in kilometers.
    """
    R = 6371  # Earth's radius in kilometers
    
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)
    
    a = math.sin(delta_lat / 2) ** 2 + \
        math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    
    return R * c


def find_nearest_beautician(
    customer_lat: float, 
    customer_lon: float, 
    beauticians: list,
    max_distance: Optional[float] = None
) -> Tuple[Optional[object], Optional[float]]:
    """
    Find the nearest available beautician to a customer location.
    
    Args:
        customer_lat: Customer latitude
        customer_lon: Customer longitude
        beauticians: List of beautician objects with latitude and longitude
        max_distance: Maximum distance in kilometers (optional)
    
    Returns:
        Tuple of (nearest beautician, distance in km) or (None, None) if none found
    """
    if not beauticians:
        return None, None
    
    nearest = None
    min_distance = float('inf')
    
    for beautician in beauticians:
        if beautician.latitude is None or beautician.longitude is None:
            continue
            
        distance = calculate_distance(
            customer_lat, customer_lon,
            float(beautician.latitude), float(beautician.longitude)
        )
        
        if distance < min_distance:
            if max_distance is None or distance <= max_distance:
                min_distance = distance
                nearest = beautician
    
    if nearest is None:
        return None, None
    
    return nearest, min_distance


def validate_coordinates(latitude: float, longitude: float) -> bool:
    """Validate that coordinates are within valid ranges."""
    return -90 <= latitude <= 90 and -180 <= longitude <= 180


def format_duration(minutes: int) -> str:
    """Format minutes into hours and minutes string."""
    hours = minutes // 60
    mins = minutes % 60
    if hours > 0:
        return f"{hours}h {mins}m" if mins > 0 else f"{hours}h"
    return f"{mins}m"


class CacheKeyGenerator:
    """Utility class for generating cache keys."""
    
    @staticmethod
    def beautician_availability(beautician_id: int, date: str) -> str:
        return f"beautician:{beautician_id}:availability:{date}"
    
    @staticmethod
    def booking_lock(booking_id: int) -> str:
        return f"booking:{booking_id}:lock"
    
    @staticmethod
    def user_bookings(user_id: int) -> str:
        return f"user:{user_id}:bookings"
