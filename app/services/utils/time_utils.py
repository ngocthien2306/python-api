from datetime import datetime, timedelta
from typing import Dict, Any


class TimeUtilities:
    """Utility functions for time-related operations"""
    
    @staticmethod
    def parse_time_string(time_str: str) -> datetime:
        """Parse time string in HH:MM format"""
        try:
            return datetime.strptime(time_str, "%H:%M")
        except ValueError:
            raise ValueError(f"Invalid time format: {time_str}. Expected HH:MM")
    
    @staticmethod
    def calculate_time_gap(start_time: str, end_time: str) -> int:
        """Calculate gap in minutes between two time strings"""
        try:
            start = TimeUtilities.parse_time_string(start_time)
            end = TimeUtilities.parse_time_string(end_time)
            
            # Handle next day case
            if end < start:
                end = end.replace(day=end.day + 1)
            
            gap = (end - start).total_seconds() / 60
            return int(gap)
        except ValueError:
            return 0
    
    @staticmethod
    def add_minutes_to_time(time_str: str, minutes: int) -> str:
        """Add minutes to a time string"""
        try:
            time_obj = TimeUtilities.parse_time_string(time_str)
            new_time = time_obj + timedelta(minutes=minutes)
            return new_time.strftime("%H:%M")
        except ValueError:
            return time_str
    
    @staticmethod
    def get_week_start_end(date: datetime) -> tuple[datetime, datetime]:
        """Get start and end of week for given date"""
        start_of_week = date - timedelta(days=date.weekday())  # Monday
        end_of_week = start_of_week + timedelta(days=6)  # Sunday
        return start_of_week, end_of_week
    
    @staticmethod
    def format_duration(minutes: int) -> str:
        """Format duration in minutes to human-readable string"""
        if minutes < 60:
            return f"{minutes}m"
        
        hours = minutes // 60
        remaining_minutes = minutes % 60
        
        if remaining_minutes == 0:
            return f"{hours}h"
        else:
            return f"{hours}h {remaining_minutes}m"
    
    @staticmethod
    def is_business_hours(time_str: str) -> bool:
        """Check if time is within business hours (9AM-6PM)"""
        try:
            time_obj = TimeUtilities.parse_time_string(time_str)
            hour = time_obj.hour
            return 9 <= hour < 18
        except ValueError:
            return False
    
    @staticmethod
    def get_next_business_day(date: datetime) -> datetime:
        """Get next business day (Monday-Friday)"""
        next_day = date + timedelta(days=1)
        
        # Skip weekends
        while next_day.weekday() >= 5:  # Saturday = 5, Sunday = 6
            next_day += timedelta(days=1)
        
        return next_day