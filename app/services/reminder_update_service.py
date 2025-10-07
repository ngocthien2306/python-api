from datetime import datetime, timedelta
from typing import Dict, Any
import logging
import os
from app.repositories.reminder import ReminderRepository
from app.repositories.task import TaskRepository
from app.repositories.user import UserRepository
from app.core.database import get_database
from app.utils.timezone_helper import utc_now, from_user_timezone, to_utc
from bson import ObjectId

# Setup file logging for reminder updates
def setup_reminder_update_logger():
    logger = logging.getLogger('reminder_updates')
    logger.setLevel(logging.INFO)
    
    # Create logs directory if it doesn't exist
    log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'logs')
    os.makedirs(log_dir, exist_ok=True)
    
    # Create file handler
    log_file = os.path.join(log_dir, 'reminder_updates.log')
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(logging.INFO)
    
    # Create console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    
    # Add handlers to logger (avoid duplicates)
    if not logger.handlers:
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
    
    return logger

logger = setup_reminder_update_logger()

class ReminderUpdateService:
    def __init__(self):
        self.db = get_database()
        self.reminder_repository = ReminderRepository(self.db)
        self.task_repository = TaskRepository(self.db)
        self.user_repository = UserRepository(self.db)
    
    def parse_before_due_to_minutes(self, before_due: str) -> int:
        """Parse beforeDue string to minutes.
        
        Supports formats like: '15m', '1h', '2h30m', '1d', etc.
        """
        try:
            before_due = before_due.lower().strip()
            total_minutes = 0
            
            # Parse days
            if 'd' in before_due:
                parts = before_due.split('d')
                if parts[0].isdigit():
                    total_minutes += int(parts[0]) * 24 * 60
                before_due = parts[1] if len(parts) > 1 else ''
            
            # Parse hours
            if 'h' in before_due:
                parts = before_due.split('h')
                if parts[0].isdigit():
                    total_minutes += int(parts[0]) * 60
                before_due = parts[1] if len(parts) > 1 else ''
            
            # Parse minutes
            if 'm' in before_due:
                parts = before_due.split('m')
                if parts[0].isdigit():
                    total_minutes += int(parts[0])
            elif before_due.isdigit():
                # If only number without unit, assume minutes
                total_minutes += int(before_due)
            
            return max(total_minutes, 1)  # Minimum 1 minute
            
        except Exception as e:
            logger.error(f"Error parsing before_due '{before_due}': {str(e)}")
            return 15  # Default to 15 minutes
    
    def calculate_trigger_time(self, task_due_date: datetime, task_due_time: str, before_due: str, user_timezone: str = None) -> datetime:
        """Calculate trigger time for reminder based on task due date/time and beforeDue."""
        try:
            # Default timezone if not provided
            user_tz = user_timezone or 'UTC'
            
            # Combine due date and time
            if task_due_time:
                # Parse time string (e.g., "14:30" or "2:30 PM")
                try:
                    if 'AM' in task_due_time.upper() or 'PM' in task_due_time.upper():
                        due_datetime_str = f"{task_due_date.strftime('%Y-%m-%d')} {task_due_time}"
                        due_datetime_naive = datetime.strptime(due_datetime_str, "%Y-%m-%d %I:%M %p")
                    else:
                        due_datetime_str = f"{task_due_date.strftime('%Y-%m-%d')} {task_due_time}"
                        due_datetime_naive = datetime.strptime(due_datetime_str, "%Y-%m-%d %H:%M")
                except ValueError:
                    # If time parsing fails, use end of day
                    due_datetime_naive = task_due_date.replace(hour=23, minute=59, second=59)
            else:
                # If no time specified, assume end of day
                due_datetime_naive = task_due_date.replace(hour=23, minute=59, second=59)
            
            # Convert due datetime from user timezone to UTC
            due_datetime_utc = from_user_timezone(due_datetime_naive.strftime('%Y-%m-%d %H:%M:%S'), user_tz)
            if not due_datetime_utc:
                # Fallback: assume naive datetime is already UTC
                due_datetime_utc = to_utc(due_datetime_naive)
            
            # Calculate minutes before due
            minutes_before = self.parse_before_due_to_minutes(before_due)
            
            # Calculate trigger time in UTC
            trigger_time_utc = due_datetime_utc - timedelta(minutes=minutes_before)
            
            # Ensure trigger time is not in the past
            now_utc = utc_now()
            if trigger_time_utc <= now_utc:
                # If calculated time is in the past, set it to 1 minute from now
                trigger_time_utc = now_utc + timedelta(minutes=1)
            
            return trigger_time_utc
            
        except Exception as e:
            logger.error(f"Error calculating trigger time: {str(e)}")
            # Fallback: 15 minutes from now
            return utc_now() + timedelta(minutes=15)
    
    async def update_reminders_for_task(self, task_id: str, updated_task_data: Dict[str, Any]) -> bool:
        """Update all reminders for a task when task due date/time changes."""
        try:
            current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            logger.info(f"🔄 [{current_time}] Updating reminders for task {task_id}")
            
            # Get all pending reminders for this task
            reminders = self.reminder_repository.find({
                "taskId": ObjectId(task_id),
                "status": "pending"
            })
            
            if not reminders:
                logger.info(f"ℹ️  [{current_time}] No pending reminders found for task {task_id}")
                return True
            
            # Get updated task data
            task_due_date = updated_task_data.get('due_date')
            task_due_time = updated_task_data.get('due_time', '')
            
            logger.info(f"📅 [{current_time}] Task new due date: {task_due_date}, due time: {task_due_time or 'None'}")
            logger.info(f"📋 [{current_time}] Found {len(reminders)} pending reminders to update:")
            
            for i, reminder in enumerate(reminders, 1):
                old_trigger = reminder.get('triggerTime', 'unknown')
                if isinstance(old_trigger, datetime):
                    old_trigger = old_trigger.strftime('%Y-%m-%d %H:%M:%S')
                logger.info(f"   {i}. Reminder {reminder['_id']} - beforeDue: {reminder.get('beforeDue', '15m')} - Current trigger: {old_trigger}")
            
            if not task_due_date:
                logger.warning(f"⚠️  [{current_time}] No due date found for task {task_id}, cannot update reminders")
                return False
            
            # Convert due_date to datetime if it's a string
            if isinstance(task_due_date, str):
                task_due_date = datetime.fromisoformat(task_due_date.replace('Z', '+00:00'))
            
            updated_count = 0
            
            for reminder in reminders:
                try:
                    # Get user timezone for this reminder
                    user = self.user_repository.get_user_by_username(reminder['userId'])
                    user_timezone = user.personality.timezone if user else 'UTC'
                    
                    # Calculate new trigger time
                    new_trigger_time = self.calculate_trigger_time(
                        task_due_date, 
                        task_due_time, 
                        reminder.get('beforeDue', '15m'),
                        user_timezone
                    )
                    
                    # Update reminder
                    success = self.reminder_repository.update(
                        str(reminder['_id']), 
                        {
                            "triggerTime": new_trigger_time,
                            "updatedAt": utc_now()
                        }
                    )
                    
                    if success:
                        updated_count += 1
                        new_trigger_str = new_trigger_time.strftime('%Y-%m-%d %H:%M:%S')
                        logger.info(f"✅ Updated reminder {reminder['_id']} with new trigger time: {new_trigger_str}")
                    else:
                        logger.error(f"❌ Failed to update reminder {reminder['_id']}")
                        
                except Exception as e:
                    logger.error(f"💥 Error updating reminder {reminder['_id']}: {str(e)}")
                    continue
            
            logger.info(f"🏁 [{current_time}] Updated {updated_count}/{len(reminders)} reminders for task {task_id}")
            return updated_count > 0
            
        except Exception as e:
            logger.error(f"Error updating reminders for task {task_id}: {str(e)}")
            return False
    
    async def create_reminder_for_task(self, task_id: str, user_id: str, reminder_data: Dict[str, Any]) -> bool:
        """Create a new reminder for a task."""
        try:
            # Get task data
            task = self.task_repository.get_task_by_id(task_id)
            if not task:
                logger.error(f"Task {task_id} not found")
                return False
            
            task_due_date = task.get('due_date')
            task_due_time = task.get('due_time', '')
            
            if not task_due_date:
                logger.error(f"Task {task_id} has no due date, cannot create reminder")
                return False
            
            # Convert due_date to datetime if it's a string
            if isinstance(task_due_date, str):
                task_due_date = datetime.fromisoformat(task_due_date.replace('Z', '+00:00'))
            
            # Get user timezone for trigger time calculation
            user = self.user_repository.get_user_by_username(user_id)
            user_timezone = user.personality.timezone if user else 'UTC'
            
            # Calculate trigger time
            before_due = reminder_data.get('beforeDue', '15m')
            trigger_time = self.calculate_trigger_time(task_due_date, task_due_time, before_due, user_timezone)
            
            # Create reminder document
            reminder_doc = {
                "userId": user_id,
                "taskId": ObjectId(task_id),
                "type": reminder_data.get('type', 'time'),
                "triggerTime": trigger_time,
                "beforeDue": before_due,
                "message": reminder_data.get('message', f"Reminder: {task['title']} due in {before_due}"),
                "channel": reminder_data.get('channel', 'notification'),
                "status": "pending",
                "priority": reminder_data.get('priority', 'medium'),
                "scheduleType": reminder_data.get('scheduleType', ''),
                "slotIndex": reminder_data.get('slotIndex', 0),
                "ruleIndex": reminder_data.get('ruleIndex', 0),
                "createdAt": utc_now(),
                "updatedAt": utc_now()
            }
            
            # Insert reminder
            result = self.reminder_repository.get_collection().insert_one(reminder_doc)
            
            if result.inserted_id:
                logger.info(f"Created reminder {result.inserted_id} for task {task_id}")
                return True
            else:
                logger.error(f"Failed to create reminder for task {task_id}")
                return False
                
        except Exception as e:
            logger.error(f"Error creating reminder for task {task_id}: {str(e)}")
            return False