from datetime import datetime


def local_now():
    """Get current local server time as naive datetime."""
    return datetime.now()


def parse_datetime_string(dt_str):
    """Parse datetime string to local datetime.
    
    Args:
        dt_str: datetime string in format 'YYYY-MM-DD HH:MM:SS' or 'YYYY-MM-DD'
        
    Returns:
        Local datetime object
    """
    if not dt_str:
        return None
        
    try:
        # Parse datetime string
        if 'T' in dt_str:
            # ISO format - strip timezone info and use as local
            dt_str = dt_str.split('+')[0].split('Z')[0]
            dt = datetime.fromisoformat(dt_str)
        elif ' ' in dt_str:
            # Format: YYYY-MM-DD HH:MM:SS
            dt = datetime.strptime(dt_str, '%Y-%m-%d %H:%M:%S')
        else:
            # Format: YYYY-MM-DD
            dt = datetime.strptime(dt_str, '%Y-%m-%d')
            
        return dt
        
    except Exception as e:
        print(f"Error parsing datetime string: {e}")
        return None


def format_datetime(dt, date_only=False):
    """Format datetime for display.
    
    Args:
        dt: datetime object
        date_only: if True, return only date part
        
    Returns:
        formatted string
    """
    if not dt:
        return None
        
    if date_only:
        return dt.strftime('%Y-%m-%d')
    else:
        return dt.strftime('%Y-%m-%d %H:%M:%S')