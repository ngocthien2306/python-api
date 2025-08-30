from typing import Dict, Any, List
from datetime import datetime
from app.repositories.base import BaseRepository
from app.models.schedule import Schedule

class ScheduleRepository(BaseRepository[Schedule]):
    def get_collection_name(self) -> str:
        return "schedules"
    
    def find_by_user_and_date(self, user_id: str, date: datetime) -> Dict[str, Any]:
        return self.get_collection().find_one({
            "userId": user_id,
            "date": date
        })
    
    def find_weekly_schedules(self, user_id: str, start_date: datetime, end_date: datetime) -> List[Dict[str, Any]]:
        return self.find({
            "userId": user_id,
            "date": {"$gte": start_date, "$lte": end_date}
        })