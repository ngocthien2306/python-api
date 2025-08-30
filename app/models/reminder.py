from datetime import datetime
from app.models.base import BaseModel
from bson import ObjectId

class Reminder(BaseModel):
    def __init__(self, user_id: str, task_id: ObjectId):
        super().__init__()
        self.user_id = user_id
        self.task_id = task_id
        self.type: str = "time"
        self.trigger_time: datetime = datetime.now()
        self.before_due: str = "15m"
        self.message: str = ""
        self.channel: str = "notification"
        self.status: str = "pending"
        self.priority: str = "medium"
        self.schedule_type: str = ""
        self.slot_index: int = 0
        self.rule_index: int = 0