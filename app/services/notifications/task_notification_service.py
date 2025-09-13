from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from app.services.notifications.web_push_service import web_push_manager
from app.repositories.user import UserRepository
from app.repositories.task import TaskRepository
from app.core.database import get_database

class TaskNotificationService:
    def __init__(self):
        self.web_push_manager = web_push_manager
        self.db = get_database()
        self.user_repo = UserRepository(self.db)
        self.task_repo = TaskRepository(self.db)
    
    async def send_task_due_notification(self, task_id: str, user_id: str):
        """Send notification when task is due"""
        try:
            task = self.task_repo.get_task_by_id(task_id)
            if not task:
                return False
            
            # Prepare notification payload
            payload = {
                "title": f"Task Due: {task.title}",
                "body": f"Your task '{task.title}' is due now!",
                "icon": "/icon-192x192.png",
                "badge": "/badge-72x72.png",
                "data": {
                    "task_id": task_id,
                    "action_url": f"/calendar?task={task_id}",
                    "notification_type": "task_due",
                    "priority": task.priority
                },
                "actions": [
                    {
                        "action": "complete",
                        "title": "Mark Complete"
                    },
                    {
                        "action": "snooze",
                        "title": "Snooze 1h"
                    },
                    {
                        "action": "view",
                        "title": "View Task"
                    }
                ],
                "requireInteraction": True,
                "tag": f"task-due-{task_id}"
            }
            
            return await self.web_push_manager.send_to_user(user_id, payload)
            
        except Exception as e:
            print(f"Error sending task due notification: {str(e)}")
            return False
    
    async def send_task_reminder_notification(self, task_id: str, user_id: str, minutes_before: int = 30):
        """Send reminder notification before task is due"""
        try:
            task = self.task_repo.get_task_by_id(task_id)
            if not task:
                return False
            
            # Prepare notification payload
            payload = {
                "title": f"Task Reminder: {task.title}",
                "body": f"Your task '{task.title}' is due in {minutes_before} minutes",
                "icon": "/icon-192x192.png",
                "badge": "/badge-72x72.png",
                "data": {
                    "task_id": task_id,
                    "action_url": f"/calendar?task={task_id}",
                    "notification_type": "task_reminder",
                    "minutes_before": minutes_before,
                    "priority": task.priority
                },
                "actions": [
                    {
                        "action": "view",
                        "title": "View Task"
                    },
                    {
                        "action": "snooze",
                        "title": "Remind Later"
                    }
                ],
                "tag": f"task-reminder-{task_id}"
            }
            
            return await self.web_push_manager.send_to_user(user_id, payload)
            
        except Exception as e:
            print(f"Error sending task reminder notification: {str(e)}")
            return False
    
    async def send_task_created_notification(self, task_id: str, user_id: str):
        """Send notification when new task is created"""
        try:
            task = self.task_repo.get_task_by_id(task_id)
            if not task:
                return False
            
            # Prepare notification payload
            payload = {
                "title": "New Task Created",
                "body": f"Task '{task.title}' has been created",
                "icon": "/icon-192x192.png",
                "badge": "/badge-72x72.png",
                "data": {
                    "task_id": task_id,
                    "action_url": f"/calendar?task={task_id}",
                    "notification_type": "task_created",
                    "priority": task.priority
                },
                "actions": [
                    {
                        "action": "view",
                        "title": "View Task"
                    }
                ],
                "tag": f"task-created-{task_id}"
            }
            
            return await self.web_push_manager.send_to_user(user_id, payload)
            
        except Exception as e:
            print(f"Error sending task created notification: {str(e)}")
            return False
    
    async def send_task_updated_notification(self, task_id: str, user_id: str, changes: Dict[str, Any]):
        """Send notification when task is updated"""
        try:
            task = self.task_repo.get_task_by_id(task_id)
            if not task:
                return False
            
            # Create a summary of changes
            change_summary = []
            if "status" in changes:
                change_summary.append(f"Status: {changes['status']}")
            if "priority" in changes:
                change_summary.append(f"Priority: {changes['priority']}")
            if "due_date" in changes:
                change_summary.append(f"Due date: {changes['due_date']}")
            
            changes_text = ", ".join(change_summary) if change_summary else "Task details updated"
            
            # Prepare notification payload
            payload = {
                "title": f"Task Updated: {task.title}",
                "body": f"{changes_text}",
                "icon": "/icon-192x192.png",
                "badge": "/badge-72x72.png",
                "data": {
                    "task_id": task_id,
                    "action_url": f"/calendar?task={task_id}",
                    "notification_type": "task_updated",
                    "changes": changes,
                    "priority": task.priority
                },
                "actions": [
                    {
                        "action": "view",
                        "title": "View Task"
                    }
                ],
                "tag": f"task-updated-{task_id}"
            }
            
            return await self.web_push_manager.send_to_user(user_id, payload)
            
        except Exception as e:
            print(f"Error sending task updated notification: {str(e)}")
            return False
    
    async def send_overdue_task_notification(self, task_id: str, user_id: str):
        """Send notification for overdue tasks"""
        try:
            task = self.task_repo.get_task_by_id(task_id)
            if not task:
                return False
            
            # Calculate how overdue the task is
            if task.due_date:
                overdue_time = datetime.now() - task.due_date
                if overdue_time.days > 0:
                    overdue_text = f"{overdue_time.days} days overdue"
                else:
                    hours = overdue_time.seconds // 3600
                    overdue_text = f"{hours} hours overdue"
            else:
                overdue_text = "Overdue"
            
            # Prepare notification payload
            payload = {
                "title": f"⚠️ Overdue Task: {task.title}",
                "body": f"Your task is {overdue_text}",
                "icon": "/icon-192x192.png",
                "badge": "/badge-72x72.png",
                "data": {
                    "task_id": task_id,
                    "action_url": f"/calendar?task={task_id}",
                    "notification_type": "task_overdue",
                    "priority": "high"
                },
                "actions": [
                    {
                        "action": "complete",
                        "title": "Mark Complete"
                    },
                    {
                        "action": "reschedule",
                        "title": "Reschedule"
                    },
                    {
                        "action": "view",
                        "title": "View Task"
                    }
                ],
                "requireInteraction": True,
                "tag": f"task-overdue-{task_id}"
            }
            
            return await self.web_push_manager.send_to_user(user_id, payload)
            
        except Exception as e:
            print(f"Error sending overdue task notification: {str(e)}")
            return False
    
    async def get_upcoming_tasks(self, user_id: str, hours_ahead: int = 24) -> List[Dict]:
        """Get tasks due within specified hours"""
        try:
            end_time = datetime.now() + timedelta(hours=hours_ahead)
            tasks = self.task_repo.get_tasks_due_between(
                user_id, 
                datetime.now(), 
                end_time
            )
            
            return [
                {
                    "id": str(task.id),
                    "title": task.title,
                    "due_date": task.due_date,
                    "priority": task.priority,
                    "status": task.status
                } for task in tasks if task.status != "completed"
            ]
            
        except Exception as e:
            print(f"Error getting upcoming tasks: {str(e)}")
            return []
    
    async def schedule_task_reminders(self, task_id: str, user_id: str, reminder_times: List[int] = [30, 60, 1440]):
        """Schedule multiple reminders for a task (in minutes before due)"""
        try:
            task = self.task_repo.get_task_by_id(task_id)
            if not task or not task.due_date:
                return False
            
            scheduled_count = 0
            for minutes_before in reminder_times:
                reminder_time = task.due_date - timedelta(minutes=minutes_before)
                
                # Only schedule if reminder time is in the future
                if reminder_time > datetime.now():
                    # In a production environment, you would use a task queue like Celery
                    # For now, we'll just log the scheduled reminders
                    print(f"Scheduled reminder for task {task_id} at {reminder_time} ({minutes_before} minutes before)")
                    scheduled_count += 1
            
            return scheduled_count > 0
            
        except Exception as e:
            print(f"Error scheduling task reminders: {str(e)}")
            return False

# Global instance
task_notification_service = TaskNotificationService()