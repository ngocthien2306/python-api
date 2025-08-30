from typing import List, Dict, Any
from datetime import datetime
from app.models.base import BaseModel

class Message:
    def __init__(self, timestamp: datetime, role: str, content: str, **kwargs):
        self.timestamp = timestamp
        self.role = role
        self.content = content
        for key, value in kwargs.items():
            setattr(self, key, value)

class Conversation(BaseModel):
    def __init__(self, user_id: str, session_id: str):
        super().__init__()
        self.user_id = user_id
        self.session_id = session_id
        self.messages: List[Message] = []
        self.active_topics: List[str] = []
        self.user_mood: str = "neutral"