from app.services.database_manager import DatabaseManagerService
from app.schemas.ai_response import ProcessConversationRequest, AIResponse
from app.schemas.database import APIResponse
from typing import Dict, Any

class AIProcessorService:
    def __init__(self, db_manager: DatabaseManagerService):
        self.db_manager = db_manager
    
    def process_conversation(self, request: ProcessConversationRequest) -> APIResponse:
        try:
            result = self.db_manager.process_ai_response(
                request.parsed_response,
                request.user_input,
                request.user_id
            )
            
            if result["success"]:
                return APIResponse(success=True, results=result["results"])
            else:
                return APIResponse(
                    success=False, 
                    error=result["error"],
                    partial_results=result.get("partial_results")
                )
                
        except Exception as e:
            return APIResponse(success=False, error=str(e))