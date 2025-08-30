from typing import Dict, Any, List
from datetime import datetime, timedelta
from app.repositories.reminder import ReminderRepository
from app.repositories.task import TaskRepository
from app.models.reminder import Reminder
from bson import ObjectId


class ReminderService:
    """Service responsible for all reminder-related operations"""
    
    def __init__(self, reminder_repo: ReminderRepository, task_repo: TaskRepository):
        self.reminder_repo = reminder_repo
        self.task_repo = task_repo
    
    def create_task_reminders(self, task_id: str, task_data: Dict[str, Any], user_id: str) -> List[Dict[str, Any]]:
        """Create reminders for a regular task (non-scheduled)"""
        reminders = task_data.get("reminders", [])
        if not reminders:
            # Create default reminders if none specified
            reminders = [{"type": "time", "beforeDue": "15m"}]
        
        # Get task to calculate trigger times
        task_doc = self.task_repo.find_by_id(task_id)
        if not task_doc or not task_doc.get("dueDate"):
            return []
        
        created_reminders = []
        
        for reminder_data in reminders:
            try:
                due_datetime = task_doc["dueDate"]
                if task_doc.get("dueTime"):
                    due_time = datetime.strptime(task_doc["dueTime"], "%H:%M").time()
                    due_datetime = datetime.combine(due_datetime.date(), due_time)
                
                before_minutes = self._parse_before_due(reminder_data.get("beforeDue", "15m"))
                trigger_time = due_datetime - timedelta(minutes=before_minutes)
                
                if trigger_time > datetime.now():
                    reminder = Reminder(user_id, ObjectId(task_id))
                    reminder.type = reminder_data.get("type", "time")
                    reminder.trigger_time = trigger_time
                    reminder.before_due = reminder_data.get("beforeDue", "15m")
                    reminder.message = reminder_data.get("message") or f"Reminder: {task_doc['title']} due in {reminder_data.get('beforeDue', '15m')}"
                    
                    reminder_doc = self._convert_reminder_to_db_format(reminder)
                    reminder_id = self.reminder_repo.create(reminder_doc)
                    
                    created_reminders.append({
                        "reminder_id": reminder_id,
                        "trigger_time": trigger_time.isoformat(),
                        "message": reminder.message,
                        "before_due": reminder.before_due
                    })
            
            except Exception as e:
                print(f"Failed to create reminder: {e}")
                continue
        
        return created_reminders
    
    def create_schedule_reminders(self, task_id: str, task_data: Dict[str, Any], 
                                user_id: str, date) -> List[Dict[str, Any]]:
        """Create reminders for scheduled tasks"""
        start_time = task_data.get("startTime")
        category = task_data.get("category", "other") 
        priority = task_data.get("priority", "medium")
        
        if not start_time:
            return []
        
        created_reminders = []
        
        try:
            # Parse start time
            start_datetime = datetime.combine(
                date,
                datetime.strptime(start_time, "%H:%M").time()
            )
            
            # Define reminder rules based on task type and priority
            reminder_rules = self._get_reminder_rules(category, priority)
            
            for rule in reminder_rules:
                trigger_time = start_datetime - timedelta(minutes=rule["minutes"])
                
                # Only create reminder if it's in the future
                if trigger_time > datetime.now():
                    reminder = Reminder(user_id, ObjectId(task_id))
                    reminder.type = "schedule"
                    reminder.trigger_time = trigger_time
                    reminder.before_due = f"{rule['minutes']}m"
                    reminder.message = rule["message"].format(
                        task=task_data.get("title", "Task"),
                        time=start_time
                    )
                    reminder.channel = "notification"
                    reminder.priority = rule["priority"]
                    reminder.schedule_type = "auto-generated"
                    
                    reminder_doc = self._convert_reminder_to_db_format(reminder)
                    reminder_id = self.reminder_repo.create(reminder_doc)
                    
                    created_reminders.append({
                        "reminder_id": reminder_id,
                        "trigger_time": trigger_time.isoformat(),
                        "message": reminder.message,
                        "before_start": rule["minutes"]
                    })
        
        except Exception as e:
            print(f"Failed to create schedule reminders: {e}")
        
        return created_reminders
    
    def get_upcoming_reminders(self, user_id: str, hours_ahead: int = 24) -> List[Dict[str, Any]]:
        """Get upcoming reminders for user"""
        try:
            now = datetime.now()
            end_time = now + timedelta(hours=hours_ahead)
            
            reminder_query = {
                "userId": user_id,
                "status": "pending",
                "triggerTime": {"$gte": now, "$lte": end_time}
            }
            
            reminders = self.reminder_repo.find_by_query(
                reminder_query, 
                sort=[("triggerTime", 1)],
                limit=50
            )
            
            result = []
            for reminder in reminders:
                # Get associated task
                task_id = reminder.get("taskId")
                task = None
                if task_id:
                    task = self.task_repo.find_by_id(str(task_id))
                
                result.append({
                    "reminder_id": str(reminder.get("_id", reminder.get("id"))),
                    "trigger_time": reminder["triggerTime"].isoformat(),
                    "message": reminder["message"],
                    "task_title": task["title"] if task else "Unknown Task",
                    "task_id": str(task_id) if task_id else None,
                    "type": reminder.get("type", "time"),
                    "priority": reminder.get("priority", "medium")
                })
            
            return result
            
        except Exception as e:
            print(f"Error fetching upcoming reminders: {e}")
            return []
    
    def mark_reminder_sent(self, reminder_id: str) -> bool:
        """Mark reminder as sent"""
        try:
            update_data = {
                "status": "sent",
                "sentAt": datetime.now()
            }
            
            result = self.reminder_repo.update(reminder_id, update_data)
            return result is not None
            
        except Exception as e:
            print(f"Error marking reminder as sent: {e}")
            return False
    
    def delete_reminders_by_task_id(self, task_id: str) -> bool:
        """Delete all reminders associated with a task"""
        try:
            self.reminder_repo.delete_by_task_id(task_id)
            return True
        except Exception as e:
            print(f"Error deleting reminders for task {task_id}: {e}")
            return False
    
    def get_user_reminders_summary(self, user_id: str) -> Dict[str, Any]:
        """Get reminder summary for user"""
        try:
            reminder_query = {"userId": user_id, "status": "pending"}
            reminder_count = len(self.reminder_repo.find_by_query(reminder_query, limit=1000))
            
            return {
                "success": True,
                "pending_reminders": reminder_count
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _convert_reminder_to_db_format(self, reminder: Reminder) -> Dict[str, Any]:
        """Convert Reminder model to database format"""
        reminder_doc = reminder.to_dict()
        reminder_doc["userId"] = reminder_doc.pop("user_id")
        reminder_doc["taskId"] = reminder_doc.pop("task_id")
        reminder_doc["triggerTime"] = reminder_doc.pop("trigger_time")
        reminder_doc["beforeDue"] = reminder_doc.pop("before_due")
        reminder_doc["scheduleType"] = reminder_doc.pop("schedule_type")
        reminder_doc["slotIndex"] = reminder_doc.pop("slot_index")
        reminder_doc["ruleIndex"] = reminder_doc.pop("rule_index")
        reminder_doc["createdAt"] = reminder_doc.pop("created_at")
        reminder_doc["updatedAt"] = reminder_doc.pop("updated_at")
        return reminder_doc
    
    def _get_reminder_rules(self, category: str, priority: str) -> List[Dict[str, Any]]:
        """Get reminder rules based on task category and priority"""
        base_rules = []
        
        # Category-specific rules
        if category == "meeting":
            base_rules = [
                {"minutes": 15, "message": "Chuẩn bị meeting '{task}' trong 15 phút (lúc {time})", "priority": "high"},
                {"minutes": 5, "message": "Meeting '{task}' bắt đầu trong 5 phút!", "priority": "urgent"}
            ]
        
        elif category == "deep_work" or category == "work":
            base_rules = [
                {"minutes": 30, "message": "Chuẩn bị focus work '{task}' trong 30 phút", "priority": "medium"},
                {"minutes": 10, "message": "Bắt đầu '{task}' trong 10 phút (lúc {time})", "priority": "high"}
            ]
        
        elif category == "communication":
            base_rules = [
                {"minutes": 10, "message": "Chuẩn bị gọi điện '{task}' trong 10 phút", "priority": "medium"},
                {"minutes": 2, "message": "Gọi điện '{task}' ngay bây giờ (lúc {time})!", "priority": "high"}
            ]
        
        elif category == "admin":
            base_rules = [
                {"minutes": 15, "message": "Task admin '{task}' bắt đầu trong 15 phút", "priority": "low"}
            ]
        
        else:  # default for other categories
            base_rules = [
                {"minutes": 15, "message": "Task '{task}' bắt đầu trong 15 phút (lúc {time})", "priority": "medium"}
            ]
        
        # Priority adjustments
        if priority == "urgent":
            # Add extra urgent reminder
            base_rules.append({
                "minutes": 1, 
                "message": "🚨 URGENT: '{task}' bắt đầu NGAY BÂY GIỜ!", 
                "priority": "urgent"
            })
        
        elif priority == "high":
            # Add early warning
            base_rules.insert(0, {
                "minutes": 60,
                "message": "High priority task '{task}' sẽ bắt đầu trong 1 tiếng (lúc {time})",
                "priority": "medium"
            })
        
        return base_rules
    
    def _parse_before_due(self, before_str: str) -> int:
        """Parse beforeDue string to minutes"""
        mapping = {
            "15m": 15, "30m": 30, "1h": 60, "2h": 120, "1d": 1440,
            "5m": 5, "10m": 10, "45m": 45, "3h": 180, "4h": 240
        }
        return mapping.get(before_str, 15)