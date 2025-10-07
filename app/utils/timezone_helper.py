from datetime import datetime, timezone
from zoneinfo import ZoneInfo


def utc_now():
    """Get current UTC time as timezone-aware datetime."""
    return datetime.now(timezone.utc)


def to_utc(dt):
    """Convert datetime to UTC timezone.
    
    Args:
        dt: datetime object (naive or timezone-aware)
        
    Returns:
        timezone-aware UTC datetime
    """
    if dt is None:
        return None
        
    if dt.tzinfo is None:
        # Assume naive datetime is already UTC
        return dt.replace(tzinfo=timezone.utc)
    else:
        # Convert timezone-aware datetime to UTC
        return dt.astimezone(timezone.utc)


def from_user_timezone(dt_str, user_timezone_str):
    """Convert datetime string from user timezone to UTC.
    
    Args:
        dt_str: datetime string in format 'YYYY-MM-DD HH:MM:SS' or 'YYYY-MM-DD'
        user_timezone_str: timezone string like 'Asia/Ho_Chi_Minh'
        
    Returns:
        UTC datetime object
    """
    if not dt_str or not user_timezone_str:
        return None
        
    try:
        # Parse datetime string
        if 'T' in dt_str:
            # ISO format
            dt_str = dt_str.replace('Z', '+00:00')
            dt = datetime.fromisoformat(dt_str)
        elif ' ' in dt_str:
            # Format: YYYY-MM-DD HH:MM:SS
            dt = datetime.strptime(dt_str, '%Y-%m-%d %H:%M:%S')
        else:
            # Format: YYYY-MM-DD
            dt = datetime.strptime(dt_str, '%Y-%m-%d')
            
        # If naive datetime, assume it's in user timezone
        if dt.tzinfo is None:
            user_tz = ZoneInfo(user_timezone_str)
            dt = dt.replace(tzinfo=user_tz)
            
        # Convert to UTC
        return dt.astimezone(timezone.utc)
        
    except Exception as e:
        print(f"Error converting datetime from user timezone: {e}")
        return None


def to_user_timezone(utc_dt, user_timezone_str):
    """Convert UTC datetime to user timezone.
    
    Args:
        utc_dt: UTC datetime object
        user_timezone_str: timezone string like 'Asia/Ho_Chi_Minh'
        
    Returns:
        datetime object in user timezone
    """
    if not utc_dt or not user_timezone_str:
        return utc_dt
        
    try:
        # Ensure UTC datetime is timezone-aware
        if utc_dt.tzinfo is None:
            utc_dt = utc_dt.replace(tzinfo=timezone.utc)
            
        # Convert to user timezone
        user_tz = ZoneInfo(user_timezone_str)
        return utc_dt.astimezone(user_tz)
        
    except Exception as e:
        print(f"Error converting datetime to user timezone: {e}")
        return utc_dt


def format_for_user(utc_dt, user_timezone_str, date_only=False):
    """Format UTC datetime for display to user in their timezone.
    
    Args:
        utc_dt: UTC datetime object
        user_timezone_str: timezone string like 'Asia/Ho_Chi_Minh'  
        date_only: if True, return only date part
        
    Returns:
        formatted string
    """
    if not utc_dt:
        return None
        
    user_dt = to_user_timezone(utc_dt, user_timezone_str)
    
    if date_only:
        return user_dt.strftime('%Y-%m-%d')
    else:
        return user_dt.strftime('%Y-%m-%d %H:%M:%S')