from datetime import datetime
from typing import List, Dict, Any
import asyncio
import logging
import httpx
from zoneinfo import ZoneInfo
from app.utils.timezone_helper import to_user_timezone
from app.services.email_service import EmailService
from app.repositories.user import UserRepository
from app.repositories.task import TaskRepository
from app.repositories.reminder import ReminderRepository
from app.core.database import get_database

logger = logging.getLogger(__name__)

class ReminderEmailService:
    def __init__(self):
        self.email_service = EmailService()
        self.db = get_database()
        self.user_repository = UserRepository(self.db)
        self.task_repository = TaskRepository(self.db)
        self.reminder_repository = ReminderRepository(self.db)
        self._last_processed_reminders = []  # For detailed logging

    async def process_due_reminders(self) -> Dict[str, Any]:
        """Process all reminders that are due to be sent."""
        try:
            # Clear previous processing data
            self._last_processed_reminders = []
            
            logger.info("Starting to process due reminders")
            
            # Get all pending reminders and check if they should be sent
            now_utc = datetime.now(ZoneInfo('UTC'))
            
            logger.info(f"🔍 Current UTC time: {now_utc.strftime('%Y-%m-%d %H:%M:%S')} UTC")
            
            # Get all pending reminders for email (won't conflict with notification service)
            all_pending_reminders = self.reminder_repository.get_pending_for_email()
            logger.info(f"🔍 Total pending reminders to check: {len(all_pending_reminders)}")
            
            due_reminders = []
            
            for reminder in all_pending_reminders:
                try:
                    # Get user info to get timezone
                    user = self.user_repository.get_user_by_username(reminder['userId'])
                    if not user:
                        logger.warning(f"⚠️ User {reminder['userId']} not found for reminder {reminder['_id']}")
                        continue
                    
                    # Get user timezone
                    user_timezone = user.personality.timezone or 'Asia/Ho_Chi_Minh'
                    
                    # Get current time in user's timezone
                    now_user_local = to_user_timezone(now_utc, user_timezone)
                    
                    # Get task info for logging and validation
                    task = self.task_repository.get_task_by_id(str(reminder['taskId']))
                    if not task:
                        logger.warning(f"⚠️ Task {reminder['taskId']} not found for reminder {reminder['_id']}")
                        continue
                    
                    # Get trigger time and convert to user's local timezone
                    trigger_time = reminder.get('triggerTime')
                    if not trigger_time:
                        logger.warning(f"⚠️ Reminder {reminder['_id']} has no triggerTime")
                        continue
                    
                    if isinstance(trigger_time, str):
                        trigger_time = datetime.fromisoformat(trigger_time.replace('Z', '+00:00'))
                    
                    # Convert trigger time to user's local timezone
                    trigger_time_local = to_user_timezone(trigger_time, user_timezone)
                    
                    # Check if it's time to send reminder (current local time >= trigger local time)
                    if now_user_local >= trigger_time_local:
                        due_reminders.append(reminder)
                        logger.info(f"📧 Reminder {reminder['_id']} is due now!")
                        logger.info(f"   User timezone: {user_timezone}")
                        logger.info(f"   Task: {getattr(task, 'title', 'Unknown')}")
                        logger.info(f"   Current time (local): {now_user_local.strftime('%Y-%m-%d %H:%M:%S')}")
                        logger.info(f"   Trigger time (local): {trigger_time_local.strftime('%Y-%m-%d %H:%M:%S')}")
                    
                except Exception as e:
                    
                    logger.error(f"💥 Error processing reminder {reminder['_id']}: {str(e)}")
                    continue
            
            total_reminders = len(due_reminders)
            successful_sends = 0
            failed_sends = 0
            
            if total_reminders > 0:
                logger.info(f"Found {total_reminders} due reminders to process:")
                for i, reminder in enumerate(due_reminders, 1):
                    trigger_time = reminder.get('triggerTime', 'unknown')
                    if isinstance(trigger_time, datetime):
                        trigger_time = trigger_time.strftime('%Y-%m-%d %H:%M:%S')
                    logger.info(f"  {i}. Reminder {reminder['_id']} - User: {reminder.get('userId', 'unknown')} - Trigger: {trigger_time}")
            else:
                logger.info("No due reminders found")
            
            for reminder_data in due_reminders:
                try:
                    # success = await self.send_reminder_email(reminder_data)
                    success = False
                    # Get task info for logging
                    task = self.task_repository.get_task_by_id(str(reminder_data['taskId']))
                    task_title = getattr(task, 'title', 'Unknown Task') if task else 'Unknown Task'
                    
                    if success:
                        # Mark email as sent (doesn't affect notification status)
                        self.reminder_repository.mark_email_as_sent(str(reminder_data['_id']))
                        successful_sends += 1
                        
                        # Store for detailed logging
                        self._last_processed_reminders.append({
                            'id': str(reminder_data['_id']),
                            'user_id': reminder_data.get('userId', 'unknown'),
                            'task_title': task_title,
                            'status': 'sent'
                        })
                        
                        logger.info(f"✅ Reminder {reminder_data['_id']} sent successfully for task: {task_title}")
                    else:
                        failed_sends += 1
                        self._last_processed_reminders.append({
                            'id': str(reminder_data['_id']),
                            'user_id': reminder_data.get('userId', 'unknown'),
                            'task_title': task_title,
                            'status': 'failed'
                        })
                        logger.error(f"❌ Failed to send reminder {reminder_data['_id']} for task: {task_title}")
                        
                except Exception as e:
                    logger.error(f"💥 Error processing reminder {reminder_data['_id']}: {str(e)}")
                    failed_sends += 1
                    continue
                
                # Small delay between emails
                await asyncio.sleep(0.5)
            
            logger.info(f"Processed {total_reminders} reminders: {successful_sends} sent, {failed_sends} failed")
            
            return {
                "success": True,
                "total_reminders": total_reminders,
                "successful_sends": successful_sends,
                "failed_sends": failed_sends,
                "message": f"Processed {total_reminders} reminders"
            }
            
        except Exception as e:
            logger.error(f"Error in process_due_reminders: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to process due reminders"
            }

    async def send_reminder_email(self, reminder_data: Dict[str, Any]) -> bool:
        """Send email for a specific reminder."""
        try:
            # Get user info
            user = self.user_repository.get_user_by_username(reminder_data['userId'])
            if not user or not user.is_verified or not user.is_active:
                logger.warning(f"User {reminder_data['userId']} not found, not verified, or not active")
                return False
            
            # Get task info
            task = self.task_repository.get_task_by_id(str(reminder_data['taskId']))
            if not task:
                logger.warning(f"Task {reminder_data['taskId']} not found")
                return False
            
            # Get user display name
            username = user.profile.first_name or user.username
            
            # Prepare task data for email
            task_data = {
                'id': str(getattr(task, '_id', '')),
                'title': getattr(task, 'title', ''),
                'description': getattr(task, 'description', ''),
                'priority': getattr(task, 'priority', 'medium'),
                'category': getattr(task, 'category', 'other'),
                'due_date': getattr(task, 'due_date', None),
                'due_time': getattr(task, 'due_time', None),
                'estimated_duration': getattr(task, 'estimated_duration', 60)
            }
            
            # Format due date
            if task_data['due_date']:
                due_date = task_data['due_date']
                if isinstance(due_date, str):
                    due_date = datetime.fromisoformat(due_date.replace('Z', '+00:00'))
                task_data['due_date_formatted'] = due_date.strftime('%B %d, %Y')
            else:
                task_data['due_date_formatted'] = 'No due date'
            
            # Add reminder specific info
            reminder_info = {
                'reminder_message': reminder_data.get('message', ''),
                'before_due': reminder_data.get('beforeDue', '15m'),
                'trigger_time': reminder_data.get('triggerTime'),
                'reminder_type': reminder_data.get('type', 'time')
            }
            
            # Send email using the existing task due soon template but customized for reminders
            success = await self.email_service.send_task_reminder_notification_email(
                email=user.email,
                username=username,
                task=task_data,
                reminder=reminder_info
            )
            
            return success
            
        except Exception as e:
            logger.error(f"Error sending reminder email: {str(e)}")
            return False

    async def get_upcoming_reminders(self, user_id: str, hours_ahead: int = 24) -> List[Dict[str, Any]]:
        """Get upcoming reminders for a user."""
        try:
            upcoming_reminders = self.reminder_repository.find_upcoming(user_id, hours_ahead)
            
            # Enrich with task information
            enriched_reminders = []
            for reminder in upcoming_reminders:
                try:
                    task = self.task_repository.get_task_by_id(str(reminder['taskId']))
                    if task:
                        reminder['task'] = {
                            'title': getattr(task, 'title', ''),
                            'description': getattr(task, 'description', ''),
                            'priority': getattr(task, 'priority', 'medium'),
                            'due_date': getattr(task, 'due_date', None),
                            'due_time': getattr(task, 'due_time', None)
                        }
                    enriched_reminders.append(reminder)
                except Exception as e:
                    logger.error(f"Error enriching reminder {reminder['_id']}: {str(e)}")
                    continue
            
            return enriched_reminders
            
        except Exception as e:
            logger.error(f"Error getting upcoming reminders for user {user_id}: {str(e)}")
            return []

    async def send_test_reminder_email(self, user_id: str) -> bool:
        """Send a test reminder email with sample data."""
        try:
            user = self.user_repository.get_user_by_id(user_id)
            if not user:
                return False
            
            username = user.profile.first_name or user.username
            
            # Sample task data
            sample_task = {
                'id': 'test123',
                'title': 'Complete Project Presentation',
                'description': 'Prepare and finalize the Q4 project presentation slides',
                'priority': 'high',
                'category': 'work',
                'due_date_formatted': 'January 16, 2024',
                'due_time': '2:00 PM',
                'estimated_duration': 90
            }
            
            # Sample reminder data
            sample_reminder = {
                'reminder_message': 'Reminder: Complete Project Presentation due in 15m',
                'before_due': '15m',
                'trigger_time': datetime.now(ZoneInfo('UTC')),
                'reminder_type': 'time'
            }
            
            success = await self.email_service.send_task_reminder_notification_email(
                email=user.email,
                username=username,
                task=sample_task,
                reminder=sample_reminder
            )
            
            return success
            
        except Exception as e:
            logger.error(f"Error sending test reminder email: {str(e)}")
            return False

    def _get_user_timezone(self, user) -> ZoneInfo:
        """Get user timezone with fallback to Asia/Ho_Chi_Minh."""
        try:
            user_timezone_str = user.personality.timezone or 'Asia/Ho_Chi_Minh'
            return ZoneInfo(user_timezone_str)
        except Exception:
            logger.warning(f"⚠️ Invalid timezone {user.personality.timezone} for user {user.username}, using Asia/Ho_Chi_Minh")
            return ZoneInfo('Asia/Ho_Chi_Minh')

    async def _send_websocket_notification(self, user_id: str, task_data: dict, reminder_data: dict) -> bool:
        """Send websocket notification to user."""
        try:
            notification = {
                "type": "task_reminder",
                "title": "Task Reminder",
                "message": f"Reminder: {task_data['title']} is due soon",
                "task": task_data,
                "reminder": reminder_data,
                "priority": "medium"
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"http://localhost:8000/api/v1/send-notification/{user_id}",
                    json=notification,
                    timeout=5.0
                )
                
                if response.status_code == 200:
                    logger.info(f"✅ WebSocket notification sent to user {user_id}")
                    return True
                else:
                    logger.warning(f"⚠️ WebSocket notification failed for user {user_id}: {response.status_code}")
                    return False
                    
        except Exception as e:
            logger.error(f"💥 Error sending WebSocket notification to user {user_id}: {str(e)}")
            return False

    def _parse_before_due_to_minutes(self, before_due: str) -> int:
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