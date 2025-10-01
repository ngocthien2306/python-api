from pydantic import BaseModel
from typing import List, Dict, Any, Optional

class Message(BaseModel):
    text: str
    facialExpression: str
    animation: str

class TaskData(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    priority: Optional[str] = "medium"
    category: Optional[str] = "other"
    dueDate: Optional[str] = None
    dueTime: Optional[str] = None
    status: Optional[str] = "pending"
    tags: List[str] = []
    subtasks: List[str] = []
    reminders: List[Dict[str, Any]] = []

class TaskAction(BaseModel):
    action: str
    task: Optional[TaskData] = None  # Legacy format for single task
    tasks: Optional[List[TaskData]] = None  # New format for multiple tasks

class SchedulingTask(BaseModel):
    title: str
    startTime: Optional[str] = None
    endTime: Optional[str] = None
    duration: Optional[int] = 60
    priority: Optional[str] = "medium"
    category: Optional[str] = "other"
    flexibility: Optional[str] = "flexible"

class SchedulingAction(BaseModel):
    type: str
    action: Optional[str] = None
    timeScope: Optional[str] = None
    tasks: List[SchedulingTask] = []
    conflicts: List[Dict[str, Any]] = []

class AIResponse(BaseModel):
    mode: str
    intent: str
    confidence: float
    messages: List[Message]
    taskAction: Optional[TaskAction] = None
    schedulingAction: Optional[SchedulingAction] = None
    needsConfirmation: Optional[bool] = False
    confirmationType: Optional[str] = None
    pendingData: Optional[Dict[str, Any]] = None

class ProcessConversationRequest(BaseModel):
    parsed_response: AIResponse
    user_input: str
    user_id: str
    session_id: str
    timestamp: str
    source: str