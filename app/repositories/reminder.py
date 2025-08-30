from typing import Dict, Any, List
from datetime import datetime, timedelta
from app.repositories.base import BaseRepository
from app.models.reminder import Reminder

class ReminderRepository(BaseRepository[Reminder]):
    def get_collection_name(self) -> str:
        return "reminders"
    
    def find_upcoming(self, user_id: str, hours_ahead: int = 24) -> List[Dict[str, Any]]:
        now = datetime.now()
        end_time = now + timedelta(hours=hours_ahead)
        return self.find({
            "userId": user_id,
            "status": "pending",
            "triggerTime": {"$gte": now, "$lte": end_time}
        })
    
    def mark_as_sent(self, reminder_id: str) -> bool:
        return self.update(reminder_id, {
            "status": "sent",
            "sentAt": datetime.now()
        })