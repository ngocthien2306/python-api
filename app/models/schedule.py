from typing import List, Dict, Any
from datetime import datetime
from app.models.base import BaseModel

class TimeSlot:
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)

class Schedule(BaseModel):
    def __init__(self, user_id: str, date: datetime, schedule_type: str):
        super().__init__()
        self.user_id = user_id
        self.date = date
        self.type = schedule_type
        self.time_slots: List[TimeSlot] = []
        self.total_workload: int = 0
        self.conflicts: int = 0
        self.version: int = 1