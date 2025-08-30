from typing import List, Dict, Any, Optional
from datetime import datetime
from app.models.base import BaseModel

class Subtask:
    def __init__(self, title: str, completed: bool = False):
        self.title = title
        self.completed = completed
        self.created_at = datetime.now()

class Task(BaseModel):
    def __init__(self, user_id: str, title: str):
        super().__init__()
        self.user_id = user_id
        self.title = title
        self.description: str = ""
        self.priority: str = "medium"
        self.category: str = "other"
        self.status: str = "pending"
        self.tags: List[str] = []
        self.subtasks: List[Subtask] = []
        self.due_date: Optional[datetime] = None
        self.due_time: Optional[str] = None
        self.estimated_duration: int = 60
        self.creation_context: str = ""
        self.last_modified_by: str = "ai"
        self.scheduled_slot: Optional[Dict[str, Any]] = None