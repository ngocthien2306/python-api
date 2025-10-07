from typing import Dict, Any, List
from datetime import datetime, timedelta
from app.repositories.base import BaseRepository
from app.models.reminder import Reminder
from app.utils.timezone_helper import utc_now

class ReminderRepository(BaseRepository[Reminder]):
    def get_collection_name(self) -> str:
        return "reminders"
    
    def find_upcoming(self, user_id: str, hours_ahead: int = 24) -> List[Dict[str, Any]]:
        now = utc_now()
        end_time = now + timedelta(hours=hours_ahead)
        return self.find({
            "userId": user_id,
            "status": "pending",
            "triggerTime": {"$gte": now, "$lte": end_time}
        })
    
    def mark_as_sent(self, reminder_id: str) -> bool:
        return self.update(reminder_id, {
            "status": "sent",
            "sentAt": utc_now()
        })
    
    def mark_email_as_sent(self, reminder_id: str) -> bool:
        """Mark email as sent without affecting notification status"""
        return self.update(reminder_id, {
            "email_status": "sent",
            "email_sent_at": utc_now()
        })
    
    def mark_notification_as_sent(self, reminder_id: str) -> bool:
        """Mark notification as sent without affecting email status"""
        return self.update(reminder_id, {
            "notification_status": "sent", 
            "notification_sent_at": utc_now()
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
    
    def delete_by_task_id(self, task_id: str) -> int:
        """Delete all reminders associated with a task"""
        from bson import ObjectId
        result = self.get_collection().delete_many({"taskId": ObjectId(task_id)})
        return result.deleted_count
    
    def reset_reminder_status_for_task(self, task_id: str) -> int:
        """Reset reminder status when task time is updated - allows reminders to be sent again"""
        from bson import ObjectId
        
        update_data = {
            "email_status": "pending",
            "notification_status": "pending", 
            "socket": True,  # Re-enable socket notifications
            "updated_at": utc_now()
        }
        
        # Remove sent timestamps to indicate not sent yet
        unset_data = {
            "email_sent_at": "",
            "notification_sent_at": "",
            "sentAt": ""
        }
        
        result = self.get_collection().update_many(
            {"taskId": ObjectId(task_id)},
            {
                "$set": update_data,
                "$unset": unset_data
            }
        )
        return result.modified_count