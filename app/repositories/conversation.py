from typing import Dict, Any
from app.repositories.base import BaseRepository
from app.models.conversation import Conversation

class ConversationRepository(BaseRepository[Conversation]):
    def get_collection_name(self) -> str:
        return "conversations"
    
    def find_by_session(self, session_id: str) -> Dict[str, Any]:
        return self.get_collection().find_one({"sessionId": session_id})
    
    def find_by_user(self, user_id: str, limit: int = 10) -> list:
        return list(self.get_collection().find(
            {"userId": user_id}
        ).sort("createdAt", -1).limit(limit))
