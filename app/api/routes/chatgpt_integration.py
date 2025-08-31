from fastapi import APIRouter, Depends, HTTPException, status
from app.models.user import TokenData
from app.repositories.user import UserRepository
from app.core.auth import get_current_user_token
from app.core.database import get_database
from app.core.dependencies import get_database_manager
from app.schemas.chatgpt_integration import (
    ChatGPTPersonalizedResponse, 
    NodeAPIIntegrationRequest,
    PersonalityProfileUpdate
)
from app.schemas.ai_response import ProcessConversationRequest
from app.services.ai_processor import AIProcessorService
from typing import Dict, Any
import json
from datetime import datetime

router = APIRouter()

def get_user_repository():
    """Dependency to get user repository."""
    db = get_database()
    return UserRepository(db)

def get_current_user(
    token_data: TokenData = Depends(get_current_user_token),
    user_repo: UserRepository = Depends(get_user_repository)
):
    """Get current authenticated user."""
    user = user_repo.get_user_by_username(token_data.username)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user

@router.get("/personality-context", response_model=ChatGPTPersonalizedResponse)
async def get_personality_context_for_chatgpt(
    current_user = Depends(get_current_user),
    db_manager = Depends(get_database_manager)
):
    """Get user personality context for ChatGPT integration."""
    try:
        # Get recent conversation history for context
        conversation_history = db_manager.get_conversation_history(current_user.id, 5)
        
        # Build personality context
        personality = current_user.personality
        profile = current_user.profile
        
        # Determine recommended tone and style based on personality
        tone_mapping = {
            "friendly": "warm and approachable",
            "formal": "professional and structured", 
            "casual": "relaxed and conversational",
            "professional": "business-focused and efficient"
        }
        
        style_mapping = {
            "brief": "concise and to-the-point",
            "detailed": "comprehensive and thorough",
            "interactive": "engaging and questioning",
            "organized": "structured and methodical"
        }
        
        recommended_tone = tone_mapping.get(personality.communication_style, "helpful and balanced")
        response_style = style_mapping.get(personality.interaction_preference, "adaptive to user needs")
        
        # Build custom instructions for ChatGPT
        custom_instructions = []
        
        if personality.custom_instructions:
            custom_instructions.append(personality.custom_instructions)
        
        # Add personality-based instructions
        custom_instructions.extend([
            f"User prefers {personality.communication_style} communication style",
            f"Respond with a {personality.preferred_tone} tone",
            f"User's work style is {personality.work_style}",
            f"User is in {personality.timezone} timezone"
        ])
        
        if personality.interests:
            custom_instructions.append(f"User interests include: {', '.join(personality.interests)}")
        
        if profile.occupation:
            custom_instructions.append(f"User works as: {profile.occupation}")
        
        personality_context = {
            "communication_preferences": {
                "style": personality.communication_style,
                "tone": personality.preferred_tone,
                "interaction": personality.interaction_preference,
                "work_style": personality.work_style
            },
            "user_info": {
                "timezone": personality.timezone,
                "language": personality.language_preference,
                "interests": personality.interests,
                "occupation": profile.occupation,
                "company": profile.company
            },
            "response_guidelines": {
                "recommended_tone": recommended_tone,
                "response_style": response_style,
                "custom_instructions": " | ".join(custom_instructions)
            }
        }
        
        return ChatGPTPersonalizedResponse(
            user_id=current_user.id,
            username=current_user.username,
            personality_context=personality_context,
            conversation_history=conversation_history,
            recommended_tone=recommended_tone,
            response_style=response_style,
            custom_instructions=" | ".join(custom_instructions)
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get personality context: {str(e)}"
        )

@router.post("/save-chatgpt-response")
async def save_chatgpt_response(
    request: NodeAPIIntegrationRequest,
    current_user = Depends(get_current_user),
    db_manager = Depends(get_database_manager)
):
    """Save ChatGPT response and process it through AI processor."""
    try:
        # Validate that the request is for the current user
        if request.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot save response for different user"
            )
        
        # Create a ProcessConversationRequest from the ChatGPT response
        # This would need to be adapted based on how ChatGPT formats its responses
        # For now, we'll create a basic structure
        
        ai_response_data = {
            "mode": "conversation",
            "intent": "general_response",
            "confidence": 0.9,
            "messages": [{
                "text": request.chatgpt_response,
                "facialExpression": "neutral",
                "animation": "talking"
            }],
            "taskAction": {
                "action": "none",
                "task": None
            },
            "schedulingAction": {
                "type": "none",
                "action": None,
                "timeScope": None,
                "tasks": [],
                "conflicts": []
            }
        }
        
        # If task or schedule data provided, update the response
        if request.task_data:
            ai_response_data["taskAction"] = {
                "action": "create",
                "task": request.task_data
            }
            ai_response_data["intent"] = "task_management"
        
        if request.schedule_data:
            ai_response_data["schedulingAction"] = {
                "type": "schedule",
                "action": "create",
                "timeScope": "today",
                "tasks": [request.schedule_data],
                "conflicts": []
            }
            ai_response_data["intent"] = "scheduling"
        
        # Create ProcessConversationRequest
        from app.schemas.ai_response import AIResponse
        ai_response = AIResponse(**ai_response_data)
        
        process_request = ProcessConversationRequest(
            parsed_response=ai_response,
            user_input="ChatGPT Integration",
            user_id=current_user.id,
            session_id=request.conversation_id or f"chatgpt_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
            timestamp=datetime.utcnow().isoformat(),
            source="chatgpt"
        )
        
        # Process the conversation through AI processor
        ai_processor = AIProcessorService(db_manager)
        result = ai_processor.process_conversation(process_request)
        
        if not result.success:
            raise HTTPException(status_code=400, detail=result.error)
        
        return {
            "success": True,
            "message": "ChatGPT response processed successfully",
            "conversation_id": process_request.session_id,
            "result": result.data
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save ChatGPT response: {str(e)}"
        )

@router.put("/update-personality-from-interaction")
async def update_personality_from_interaction(
    personality_update: PersonalityProfileUpdate,
    current_user = Depends(get_current_user),
    user_repo: UserRepository = Depends(get_user_repository)
):
    """Update user personality based on ChatGPT interactions."""
    try:
        # Convert personality update to user update format
        from app.models.user import UserUpdate, UserPersonality
        
        # Get current personality
        current_personality = current_user.personality
        
        # Update personality fields that are provided
        updated_personality_data = current_personality.dict()
        
        update_data = personality_update.dict(exclude_unset=True)
        for key, value in update_data.items():
            if key in updated_personality_data and value is not None:
                updated_personality_data[key] = value
        
        updated_personality = UserPersonality(**updated_personality_data)
        
        user_update = UserUpdate(personality=updated_personality)
        
        # Update user
        updated_user = user_repo.update_user(current_user.id, user_update)
        
        if not updated_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to update personality"
            )
        
        return {
            "success": True,
            "message": "Personality updated successfully",
            "updated_personality": updated_user.personality
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update personality: {str(e)}"
        )