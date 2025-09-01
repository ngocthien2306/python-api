from datetime import datetime
import traceback
from typing import Dict, Any, Optional
from app.services.database_manager import DatabaseManagerService
from app.schemas.user_onboarding import OnboardingProfileData

class UserOnboardingService:
    def __init__(self, db_manager: DatabaseManagerService):
        self.db_manager = db_manager
    
    async def complete_onboarding(
        self, 
        user_id: str, 
        onboarding_data: OnboardingProfileData,
        completed_at: Optional[str] = None
    ) -> Dict[str, Any]:
        """Complete user onboarding with personalization data"""
        try:
            # Convert onboarding data to dict
            onboarding_dict = onboarding_data.dict()
            
            # Prepare update data for user profile
            profile_updates = {
                # Professional Info
                "occupation": onboarding_dict.get("occupation"),
                "company": onboarding_dict.get("company"),
                "industry": onboarding_dict.get("industry"),
                "position_level": onboarding_dict.get("position_level"), 
                "work_location": onboarding_dict.get("work_location"),
                
                # Update personality object
                "personality": {
                    "work_style": onboarding_dict.get("work_style", "organized"),
                    "communication_style": onboarding_dict.get("communication_style", "friendly"),
                    "interaction_preference": onboarding_dict.get("interaction_preference", "detailed"),
                    "preferred_tone": "helpful",  # Default
                    "working_hours": onboarding_dict.get("working_hours"),
                    "break_style": onboarding_dict.get("break_style"),
                    "primary_goals": onboarding_dict.get("primary_goals", []),
                    "task_priorities": onboarding_dict.get("task_priorities"),
                    "planning_horizon": onboarding_dict.get("planning_horizon"),
                    "success_metrics": onboarding_dict.get("success_metrics", []),
                    "motivation_factors": onboarding_dict.get("motivation_factors", []),
                    "learning_style": onboarding_dict.get("learning_style"),
                    "stress_management": onboarding_dict.get("stress_management", []),
                    "reminder_style": onboarding_dict.get("reminder_style"),
                    "feedback_preference": onboarding_dict.get("feedback_preference"),
                    "privacy_level": onboarding_dict.get("privacy_level"),
                    "device_usage": onboarding_dict.get("device_usage"),
                    "tech_level": onboarding_dict.get("tech_level"),
                    "notification_preferences": onboarding_dict.get("notification_preferences", [])
                },
                
                # Update interests and other fields
                "interests": onboarding_dict.get("interests", []),
                "timezone": onboarding_dict.get("timezone", "UTC"),
                "language_preference": onboarding_dict.get("language_preference", "en"),
                "custom_instructions": onboarding_dict.get("custom_instructions"),
                
                # Mark onboarding as completed
                "is_onboarding_completed": True,
                "onboarding_completed_at": completed_at or datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat()
            }
            
            # Remove None values
            profile_updates = {k: v for k, v in profile_updates.items() if v is not None}
            
            # Update user profile in database
            update_result = await self.db_manager.update_user_profile(user_id, profile_updates)
            
            if not update_result.get("success"):
                return {
                    "success": False,
                    "error": f"Failed to update user profile: {update_result.get('error')}"
                }
            
            # Get updated profile
            updated_profile = await self.db_manager.get_user_profile(user_id)
            
            return {
                "success": True,
                "updated_profile": updated_profile,
                "message": "Onboarding completed successfully"
            }
            
        except Exception as e:
            traceback.print_exc()
            return {
                "success": False,
                "error": f"Onboarding completion failed: {str(e)}"
            }
    
    async def get_onboarding_status(self, user_id: str) -> Dict[str, Any]:
        """Get user's onboarding status"""
        try:
            user_profile = await self.db_manager.get_user_profile(user_id)
            
            if not user_profile:
                return {
                    "user_id": user_id,
                    "is_onboarding_completed": False,
                    "onboarding_step": 0,
                    "completed_steps": [],
                    "skip_onboarding": False
                }
            
            return {
                "user_id": user_id,
                "is_onboarding_completed": user_profile.get("is_onboarding_completed", False),
                "onboarding_step": user_profile.get("onboarding_step", 0),
                "completed_steps": user_profile.get("completed_steps", []),
                "started_at": user_profile.get("onboarding_started_at"),
                "completed_at": user_profile.get("onboarding_completed_at"),
                "skip_onboarding": user_profile.get("skip_onboarding", False)
            }
            
        except Exception as e:
            return {
                "user_id": user_id,
                "is_onboarding_completed": False,
                "error": str(e)
            }
    
    async def skip_onboarding(self, user_id: str) -> Dict[str, Any]:
        """Mark onboarding as skipped"""
        try:
            update_data = {
                "skip_onboarding": True,
                "is_onboarding_completed": True,
                "onboarding_completed_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat()
            }
            
            result = await self.db_manager.update_user_profile(user_id, update_data)
            return result
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to skip onboarding: {str(e)}"
            }
    
    async def get_personalization_profile(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get complete personalization profile for user"""
        try:
            profile = await self.db_manager.get_user_profile(user_id)
            
            if not profile:
                return None
            
            # Flatten personality data
            personality = profile.get("personality", {})
            
            # Construct complete personalization profile
            personalization_profile = {
                # Basic profile
                "first_name": profile.get("first_name"),
                "last_name": profile.get("last_name"),
                "phone": profile.get("phone"),
                "avatar_url": profile.get("avatar_url"),
                "date_of_birth": profile.get("date_of_birth"),
                
                # Professional info
                "occupation": profile.get("occupation"),
                "company": profile.get("company"), 
                "industry": profile.get("industry"),
                "position_level": profile.get("position_level"),
                "work_location": profile.get("work_location"),
                
                # Personality & preferences (from personality object)
                "work_style": personality.get("work_style", "organized"),
                "communication_style": personality.get("communication_style", "friendly"),
                "interaction_preference": personality.get("interaction_preference", "detailed"),
                "preferred_tone": personality.get("preferred_tone", "helpful"),
                "working_hours": personality.get("working_hours"),
                "break_style": personality.get("break_style"),
                
                # Goals & motivation
                "primary_goals": personality.get("primary_goals", []),
                "task_priorities": personality.get("task_priorities"),
                "planning_horizon": personality.get("planning_horizon"),
                "success_metrics": personality.get("success_metrics", []),
                "motivation_factors": personality.get("motivation_factors", []),
                
                # Learning & growth
                "interests": profile.get("interests", []),
                "learning_style": personality.get("learning_style"),
                "stress_management": personality.get("stress_management", []),
                
                # Technical preferences
                "timezone": profile.get("timezone", "UTC"),
                "language_preference": profile.get("language_preference", "en"),
                "notification_preferences": personality.get("notification_preferences", []),
                "device_usage": personality.get("device_usage"),
                "tech_level": personality.get("tech_level"),
                
                # AI assistant settings
                "custom_instructions": profile.get("custom_instructions"),
                "reminder_style": personality.get("reminder_style"),
                "feedback_preference": personality.get("feedback_preference"),
                "privacy_level": personality.get("privacy_level"),
                
                # Onboarding status
                "is_onboarding_completed": profile.get("is_onboarding_completed", False),
                "onboarding_completed_at": profile.get("onboarding_completed_at")
            }
            
            return personalization_profile
            
        except Exception as e:
            return None
    
    async def update_personalization_profile(
        self, 
        user_id: str, 
        profile_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Update user's personalization profile"""
        try:
            # Separate personality fields from profile fields
            personality_fields = {
                "work_style", "communication_style", "interaction_preference", 
                "preferred_tone", "working_hours", "break_style", "primary_goals",
                "task_priorities", "planning_horizon", "success_metrics", 
                "motivation_factors", "learning_style", "stress_management",
                "reminder_style", "feedback_preference", "privacy_level",
                "device_usage", "tech_level", "notification_preferences"
            }
            
            # Get current profile to merge personality data
            current_profile = await self.db_manager.get_user_profile(user_id)
            current_personality = current_profile.get("personality", {}) if current_profile else {}
            
            # Separate updates
            profile_updates = {}
            personality_updates = current_personality.copy()
            
            for key, value in profile_data.items():
                if key in personality_fields:
                    personality_updates[key] = value
                else:
                    profile_updates[key] = value
            
            # Add updated personality object to profile updates
            if personality_updates:
                profile_updates["personality"] = personality_updates
            
            # Add timestamp
            profile_updates["updated_at"] = datetime.utcnow().isoformat()
            
            # Update in database
            result = await self.db_manager.update_user_profile(user_id, profile_updates)
            
            if result.get("success"):
                updated_profile = await self.get_personalization_profile(user_id)
                return {
                    "success": True,
                    "updated_profile": updated_profile
                }
            else:
                return result
                
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to update personalization profile: {str(e)}"
            }