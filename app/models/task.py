from typing import List, Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel, Field
from bson import ObjectId

class Subtask(BaseModel):
    title: str
    completed: bool = False
    created_at: datetime = Field(default_factory=datetime.now)

class Task(BaseModel):
    id: Optional[str] = Field(default=None, alias="_id")
    user_id: str
    title: str
    description: str = ""
    priority: str = "medium"  # low, medium, high, urgent
    category: str = "other"
    status: str = "pending"  # pending, in_progress, completed, cancelled
    tags: List[str] = []
    subtasks: List[Subtask] = []
    due_date: Optional[datetime] = None
    due_time: Optional[str] = None
    estimated_duration: int = 60  # in minutes
    actual_duration: Optional[int] = None  # in minutes
    creation_context: str = ""
    last_modified_by: str = "ai"
    scheduled_slot: Optional[Dict[str, Any]] = None
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    
    class Config:
        populate_by_name = True
        json_encoders = {
            ObjectId: str,
            datetime: lambda v: v.isoformat()
        }

class TaskCreate(BaseModel):
    title: str
    description: str = ""
    priority: str = "medium"
    category: str = "other"
    tags: List[str] = []
    due_date: Optional[datetime] = None
    due_time: Optional[str] = None
    estimated_duration: int = 60

class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    priority: Optional[str] = None
    category: Optional[str] = None
    status: Optional[str] = None
    tags: Optional[List[str]] = None
    due_date: Optional[datetime] = None
    due_time: Optional[str] = None
    estimated_duration: Optional[int] = None
    actual_duration: Optional[int] = None
    completed_at: Optional[datetime] = None

class TaskResponse(BaseModel):
    id: str
    user_id: str
    title: str
    description: str
    priority: str
    category: str
    status: str
    tags: List[str]
    due_date: Optional[datetime]
    due_time: Optional[str]
    estimated_duration: int
    actual_duration: Optional[int]
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime]