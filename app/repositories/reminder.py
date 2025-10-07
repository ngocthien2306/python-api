from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from app.repositories.base import BaseRepository
from app.models.reminder import Reminder
from app.utils.timezone_helper import local_now

class ReminderRepository(BaseRepository[Reminder]):
    def get_collection_name(self) -> str:
        return "reminders"
    
    def find_upcoming(self, user_id: str, hours_ahead: int = 24) -> List[Dict[str, Any]]:
        now = local_now()
        end_time = now + timedelta(hours=hours_ahead)
        return self.find({
            "userId": user_id,
            "status": "pending",
            "triggerTime": {"$gte": now, "$lte": end_time}
        })
    
    def mark_as_sent(self, reminder_id: str) -> bool:
        return self.update(reminder_id, {
            "status": "sent",
            "sentAt": local_now()
        })
    
    def mark_email_as_sent(self, reminder_id: str) -> bool:
        """Mark email as sent without affecting notification status"""
        return self.update(reminder_id, {
            "email_status": "sent",
            "email_sent_at": local_now()
        })
    
    def mark_notification_as_sent(self, reminder_id: str) -> bool:
        """Mark notification as sent without affecting email status"""
        return self.update(reminder_id, {
            "notification_status": "sent", 
            "notification_sent_at": local_now()
        })
    
    def get_pending_for_email(self) -> List[Dict[str, Any]]:
        """Get reminders pending for email sending"""
        return self.find({
            "status": "pending",
            "$or": [
                {"email_status": {"$exists": False}},
                {"email_status": "pending"}
            ]
        })
    
    def get_pending_for_notification(self) -> List[Dict[str, Any]]:
        """Get reminders pending for notification sending"""
        return self.find({
            "status": "pending",
            "$or": [
                {"notification_status": {"$exists": False}},
                {"notification_status": "pending"}
            ]
        })
    
    def get_reminder_by_id(self, reminder_id: str) -> Optional[Dict[str, Any]]:
        """Get a reminder by its ID"""
        from bson import ObjectId
        try:
            reminder = self.get_collection().find_one({"_id": ObjectId(reminder_id)})
            if reminder:
                # Convert ObjectId to string for JSON serialization
                reminder["_id"] = str(reminder["_id"])
                if "taskId" in reminder:
                    reminder["taskId"] = str(reminder["taskId"])
            return reminder
        except Exception as e:
            print(f"Error getting reminder by ID {reminder_id}: {e}")
            return None

    def update_reminder(self, reminder_id: str, update_data: Dict[str, Any]) -> bool:
        """Update a reminder by its ID"""
        from bson import ObjectId
        try:
            # Add updated timestamp
            update_data["updated_at"] = local_now()
            
            result = self.get_collection().update_one(
                {"_id": ObjectId(reminder_id)},
                {"$set": update_data}
            )
            return result.modified_count > 0
        except Exception as e:
            print(f"Error updating reminder {reminder_id}: {e}")
            return False

    def delete_by_task_id(self, task_id: str) -> int:
        """Delete all reminders associated with a task"""
        from bson import ObjectId
        result = self.get_collection().delete_many({"taskId": ObjectId(task_id)})
        return result.deleted_count
    
    def reset_reminder_status_for_task(self, task_id: str, new_due_date: datetime = None, new_due_time: str = None) -> int:
        """Reset reminder status and update triggerTime when task time is updated"""
        from bson import ObjectId
        
        # Get existing reminders for this task
        reminders = self.find({"taskId": ObjectId(task_id)})
        
        if not reminders:
            return 0
            
        updated_count = 0
        
        for reminder in reminders:
            update_data = {
                "email_status": "pending",
                "notification_status": "pending", 
                "socket": True,  # Re-enable socket notifications
                "updated_at": local_now()
            }
            
            # Calculate new trigger time if task time changed
            if new_due_date or new_due_time:
                try:
                    # Import here to avoid circular imports
                    from app.services.reminder_update_service import ReminderUpdateService
                    
                    # Get beforeDue from existing reminder
                    before_due = reminder.get('beforeDue', '15m')
                    
                    # Use existing due_date from reminder if new_due_date is None
                    due_date_to_use = new_due_date
                    if due_date_to_use is None:
                        # Try to get existing due_date from task
                        existing_due_date = reminder.get('taskDueDate')
                        if existing_due_date and isinstance(existing_due_date, datetime):
                            due_date_to_use = existing_due_date
                    
                    if due_date_to_use:
                        # Calculate new trigger time
                        reminder_service = ReminderUpdateService()
                        new_trigger_time = reminder_service.calculate_trigger_time(
                            due_date_to_use,  # Pass datetime object directly
                            new_due_time,
                            before_due
                        )
                        
                        if new_trigger_time:
                            update_data["triggerTime"] = new_trigger_time
                            print(f"🔄 Updated triggerTime for reminder {reminder['_id']}: {new_trigger_time}")
                        
                except Exception as e:
                    print(f"⚠️ Error calculating new trigger time for reminder {reminder['_id']}: {e}")
                    # Continue with status reset even if trigger time calculation fails
            
            # Remove sent timestamps to indicate not sent yet
            unset_data = {
                "email_sent_at": "",
                "notification_sent_at": "",
                "sentAt": ""
            }
            
            result = self.get_collection().update_one(
                {"_id": reminder["_id"]},
                {
                    "$set": update_data,
                    "$unset": unset_data
                }
            )
            
            if result.modified_count > 0:
                updated_count += 1
                
        return updated_count