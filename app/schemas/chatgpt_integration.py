from pydantic import BaseModel
from typing import Optional, Dict, Any, List

class ChatGPTPersonalityRequest(BaseModel):
    """Request format for ChatGPT personality integration"""
    user_message: str
    conversation_context: Optional[Dict[str, Any]] = None
    task_context: Optional[Dict[str, Any]] = None

class ChatGPTPersonalizedResponse(BaseModel):
    """Response format with personality context for ChatGPT"""
    user_id: str
    username: str
    personality_context: Dict[str, Any]
    conversation_history: Optional[List[Dict[str, Any]]] = None
    recommended_tone: str
    response_style: str
    custom_instructions: Optional[str] = None

class NodeAPIIntegrationRequest(BaseModel):
    """Request format from Node.js API to Python API"""
    user_id: str
    chatgpt_response: str
    conversation_id: Optional[str] = None
    task_data: Optional[Dict[str, Any]] = None
    schedule_data: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None

class PersonalityProfileUpdate(BaseModel):
    """Update personality profile based on user interactions"""
    communication_style: Optional[str] = None
    preferred_tone: Optional[str] = None
    interaction_preference: Optional[str] = None
    work_style: Optional[str] = None
    interests: Optional[List[str]] = None
    timezone: Optional[str] = None
    language_preference: Optional[str] = None
    custom_instructions: Optional[str] = None
    
    # Learning from interactions
    learned_preferences: Optional[Dict[str, Any]] = None
    interaction_patterns: Optional[Dict[str, Any]] = None