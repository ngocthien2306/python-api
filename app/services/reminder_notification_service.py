from datetime import datetime, timedelta
from typing import List, Dict, Any
import asyncio
import logging
import httpx
from app.utils.timezone_helper import local_now
from app.repositories.user import UserRepository
from app.repositories.task import TaskRepository
from app.repositories.reminder import ReminderRepository
from app.repositories.notification import NotificationRepository
from app.core.database import get_database
from app.models.notification import (
    NotificationCreate, 
    NotificationType, 
    NotificationPriority,
    NotificationAction,
    NotificationData,
    TaskInfo
)

logger = logging.getLogger(__name__)

class ReminderNotificationService:
    def __init__(self):
        self.db = get_database()
        self.user_repository = UserRepository(self.db)
        self.task_repository = TaskRepository(self.db)
        self.reminder_repository = ReminderRepository(self.db)
        self.notification_repository = NotificationRepository()
        self._last_processed_reminders = []  # For detailed logging

    async def process_due_reminders(self) -> Dict[str, Any]:
        """Process all notification reminders that are due to be sent."""
        try:
            # Clear previous processing data
            self._last_processed_reminders = []
            
            logger.info("Starting to process due notification reminders")
            
            # Get all pending notification reminders and check if they should be sent
            now_local = local_now()
            
            logger.info(f"🔍 Current local time: {now_local.strftime('%Y-%m-%d %H:%M:%S')}")
            
            # Get all pending reminders for notification (won't conflict with email service)
            all_pending_reminders = self.reminder_repository.get_pending_for_notification()
            logger.info(f"🔍 Total pending notification reminders to check: {len(all_pending_reminders)}")
            
            due_reminders = []
            
            for reminder in all_pending_reminders:
                try:
                    # Get user info to get timezone
                    user = self.user_repository.get_user_by_username(reminder['userId'])
                    if not user:
                        logger.warning(f"⚠️ User {reminder['userId']} not found for reminder {reminder['_id']}")
                        continue
                    
                    # Use local server time
                    now_user_local = now_local
                    
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
                    
                    # Use trigger time as local time
                    if trigger_time.tzinfo is not None:
                        trigger_time_local = trigger_time.replace(tzinfo=None)
                    else:
                        trigger_time_local = trigger_time
                    
                    # Check if we're in the notification window (beforeDue period)
                    # Parse beforeDue to get the start time for notifications
                    before_due_str = reminder.get('beforeDue', '15m')
                    before_due_minutes = self._parse_before_due_to_minutes(before_due_str)
                    
                    # Calculate notification start time (trigger_time - beforeDue)
                    notification_start_time = trigger_time_local - timedelta(minutes=before_due_minutes)
                    
                    # Check if we're in notification window and socket is enabled
                    socket_enabled = reminder.get('socket', True)  # Default to True if not set
                    
                    # If past trigger time, mark notification as sent and skip
                    if now_user_local  > trigger_time_local + timedelta(minutes=before_due_minutes) :
                        self.reminder_repository.mark_notification_as_sent(str(reminder['_id']))
                        logger.info(f"⏰ Notification reminder {reminder['_id']} past trigger time, marked as sent")
                        logger.info(f"   Current time (local): {now_user_local.strftime('%Y-%m-%d %H:%M:%S')}")
                        logger.info(f"   Trigger time (local): {trigger_time_local.strftime('%Y-%m-%d %H:%M:%S')}")
                        continue
                    
                    # Check if we're in the notification window (before trigger time)
                    if (notification_start_time <= trigger_time_local <= now_user_local and socket_enabled):
                        due_reminders.append(reminder)
                        logger.info(f"📱 Notification reminder {reminder['_id']} is due now!")
                        logger.info(f"   Using local server time")
                        logger.info(f"   Task: {getattr(task, 'title', 'Unknown')}")
                        logger.info(f"   Current time (local): {now_user_local.strftime('%Y-%m-%d %H:%M:%S')}")
                        logger.info(f"   Trigger time (local): {trigger_time_local.strftime('%Y-%m-%d %H:%M:%S')}")
                        logger.info(f"   Notification window: {notification_start_time.strftime('%Y-%m-%d %H:%M:%S')} to {trigger_time_local.strftime('%Y-%m-%d %H:%M:%S')}")
                    elif notification_start_time <= now_user_local < trigger_time_local and not socket_enabled:
                        logger.info(f"🔕 Notification reminder {reminder['_id']} in window but socket disabled by user")
                    
                except Exception as e:
                    logger.error(f"💥 Error processing notification reminder {reminder['_id']}: {str(e)}")
                    continue
            
            total_reminders = len(due_reminders)
            successful_sends = 0
            failed_sends = 0
            
            if total_reminders > 0:
                logger.info(f"Found {total_reminders} due notification reminders to process:")
                for i, reminder in enumerate(due_reminders, 1):
                    trigger_time = reminder.get('triggerTime', 'unknown')
                    if isinstance(trigger_time, datetime):
                        trigger_time = trigger_time.strftime('%Y-%m-%d %H:%M:%S')
                    logger.info(f"  {i}. Notification Reminder {reminder['_id']} - User: {reminder.get('userId', 'unknown')} - Trigger: {trigger_time}")
            else:
                logger.info("No due notification reminders found")
            
            for reminder_data in due_reminders:
                try:
                    success = await self.send_notification_reminder(reminder_data)
                    
                    # Get task info for logging
                    task = self.task_repository.get_task_by_id(str(reminder_data['taskId']))
                    task_title = getattr(task, 'title', 'Unknown Task') if task else 'Unknown Task'
                    
                    if success:
                        # Don't mark notification as sent yet - we need to keep sending until user disables
                        # Only mark when: 1) User clicks "Don't remind again", or 2) Past trigger time
                        pass
                        successful_sends += 1
                        
                        # Store for detailed logging
                        self._last_processed_reminders.append({
                            'id': str(reminder_data['_id']),
                            'user_id': reminder_data.get('userId', 'unknown'),
                            'task_title': task_title,
                            'status': 'sent'
                        })
                        
                        logger.info(f"✅ Notification reminder {reminder_data['_id']} sent successfully for task: {task_title}")
                    else:
                        failed_sends += 1
                        self._last_processed_reminders.append({
                            'id': str(reminder_data['_id']),
                            'user_id': reminder_data.get('userId', 'unknown'),
                            'task_title': task_title,
                            'status': 'failed'
                        })
                        logger.error(f"❌ Failed to send notification reminder {reminder_data['_id']} for task: {task_title}")
                        
                except Exception as e:
                    logger.error(f"💥 Error processing notification reminder {reminder_data['_id']}: {str(e)}")
                    failed_sends += 1
                    continue
                
                # Small delay between notifications
                await asyncio.sleep(0.5)
            
            logger.info(f"Processed {total_reminders} notification reminders: {successful_sends} sent, {failed_sends} failed")
            
            return {
                "success": True,
                "total_reminders": total_reminders,
                "successful_sends": successful_sends,
                "failed_sends": failed_sends,
                "message": f"Processed {total_reminders} notification reminders"
            }
            
        except Exception as e:
            logger.error(f"Error in process_due_reminders: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to process due notification reminders"
            }

    async def send_notification_reminder(self, reminder_data: Dict[str, Any]) -> bool:
        """Send notification for a specific reminder."""
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
            
            # Check if notification already exists in database
            existing_notification = self.notification_repository.find_by_reminder_id(str(reminder_data['_id']))
            
            if not existing_notification:
                # Only create notification in database once
                success = await self._create_notification_in_db(reminder_data, user, task)
                if not success:
                    return False
                
                # Get the created notification
                existing_notification = self.notification_repository.find_by_reminder_id(str(reminder_data['_id']))
            
            # Always send via WebSocket (continuous notifications)
            websocket_success = await self._send_websocket_notification(str(user.id), existing_notification)
            
            # Record delivery attempt if websocket was sent
            if websocket_success:
                self.notification_repository.record_delivery(
                    existing_notification.id, 
                    "websocket", 
                    success=True
                )
            
            return websocket_success
            
        except Exception as e:
            logger.error(f"Error sending notification reminder: {str(e)}")
            return False

    async def _create_notification_in_db(self, reminder_data: Dict[str, Any], user, task) -> bool:
        """Create notification in database (only called once per reminder)."""
        try:
            # Prepare task data for notification
            task_data = {
                'id': str(reminder_data['taskId']),
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
            
            # Convert datetime to string if needed
            due_date_str = task_data['due_date']
            if due_date_str and hasattr(due_date_str, 'isoformat'):
                due_date_str = due_date_str.isoformat()
            elif due_date_str:
                due_date_str = str(due_date_str)
            
            # Create notification data models
            task_info = TaskInfo(
                id=task_data['id'],
                title=task_data['title'],
                priority=task_data['priority'],
                status=getattr(task, 'status', 'pending'),
                due_date=due_date_str,
                due_time=task_data['due_time'],
                category=task_data['category']
            )
            
            action = NotificationAction(
                type="navigate",
                url="/calendar"
            )
            
            data = NotificationData(
                task=task_info,
                extra={
                    "notification_type": "task_reminder",
                    "reminder_message": reminder_data.get('message', ''),
                    "before_due": reminder_data.get('beforeDue', '15m'),
                    "reminder_id": str(reminder_data['_id'])
                }
            )
            
            # Get user timezone for timestamps
            user_timezone = user.personality.timezone or 'Asia/Ho_Chi_Minh'
            
            # Create timestamps in local time
            now_user_local = local_now()
            
            # Create notification in database with user local timestamps
            notification_create = NotificationCreate(
                user_id=str(user.id),
                title="📋 Task Reminder",
                body=reminder_data.get('message', f"Reminder: {task_data['title']} is due soon"),
                type=NotificationType.TASK_REMINDER,
                priority=NotificationPriority.MEDIUM,
                action=action,
                data=data,
                created_at=now_user_local,  # Use user local time
                updated_at=now_user_local,  # Use user local time
                metadata={
                    "source": "reminder_notification_service",
                    "reminder_id": str(reminder_data['_id']),
                    "trigger_time": reminder_data.get('triggerTime')
                }
            )
            
            # Save to database
            self.notification_repository.create_notification(notification_create)
            logger.info(f"💾 Created notification in database for reminder {reminder_data['_id']}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error creating notification in database: {str(e)}")
            return False

    async def _send_websocket_notification(self, user_id: str, stored_notification) -> bool:
        """Send websocket notification to user with detailed toast information."""
        try:
            # Extract detailed task information for toast display
            task_info = None
            reminder_info = None
            
            if stored_notification.data and stored_notification.data.task:
                task = stored_notification.data.task
                task_info = {
                    "id": task.id,
                    "title": task.title,
                    "priority": task.priority,
                    "status": task.status,
                    "due_date": task.due_date,
                    "due_time": task.due_time,
                    "category": task.category
                }
            
            if stored_notification.data and stored_notification.data.extra:
                extra = stored_notification.data.extra
                reminder_info = {
                    "before_due": extra.get("before_due", "15m"),
                    "reminder_message": extra.get("reminder_message", ""),
                    "reminder_id": extra.get("reminder_id")
                }
            
            # Enhanced notification payload with detailed information
            notification_payload = {
                "type": "task_notification",
                "id": stored_notification.id,
                "title": stored_notification.title,
                "body": stored_notification.body,
                "priority": stored_notification.priority,
                "action": stored_notification.action.dict() if stored_notification.action else None,
                "data": stored_notification.data.dict() if stored_notification.data else None,
                "created_at": stored_notification.created_at.isoformat(),
                "stored": True,
                # Enhanced fields for detailed toast display
                "toast": {
                    "show_details": True,
                    "task": task_info,
                    "reminder": reminder_info,
                    "timestamp": stored_notification.created_at.isoformat(),
                    "formatted_time": stored_notification.created_at.strftime('%H:%M'),
                    "formatted_date": stored_notification.created_at.strftime('%d/%m/%Y')
                }
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"https://task-agent-api.ngrok.dev/api/v1/send-notification/{user_id}",
                    json=notification_payload,
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

    async def get_upcoming_notification_reminders(self, user_id: str, hours_ahead: int = 24) -> List[Dict[str, Any]]:
        """Get upcoming notification reminders for a user."""
        try:
            upcoming_reminders = self.reminder_repository.find({
                "userId": user_id,
                "status": "pending"
            })
            
            # Filter by time range and enrich with task information
            enriched_reminders = []
            now_local = local_now()
            cutoff_time = now_local + timedelta(hours=hours_ahead)
            
            for reminder in upcoming_reminders:
                try:
                    trigger_time = reminder.get('triggerTime')
                    if trigger_time and isinstance(trigger_time, str):
                        trigger_time = datetime.fromisoformat(trigger_time.replace('Z', '+00:00'))
                    
                    if trigger_time:
                        if trigger_time.tzinfo is not None:
                            trigger_time = trigger_time.replace(tzinfo=None)
                        
                        if now_local <= trigger_time <= cutoff_time:
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
                    logger.error(f"Error enriching notification reminder {reminder['_id']}: {str(e)}")
                    continue
            
            return enriched_reminders
            
        except Exception as e:
            logger.error(f"Error getting upcoming notification reminders for user {user_id}: {str(e)}")
            return []

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