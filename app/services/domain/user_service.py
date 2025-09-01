from typing import Dict, Any, Optional
from datetime import datetime, timezone
from app.repositories.user import UserRepository
import traceback


class UserService:
    """
    Domain service for user profile operations
    Follows Single Responsibility Principle - handles only user profile business logic
    """
    
    def __init__(self, user_repository: UserRepository):
        self.user_repository = user_repository
    
    async def get_user_profile(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user profile data with proper field mapping for onboarding"""
        try:
            user = self.user_repository.get_user_by_id(user_id)
            if not user:
                return None
            
            # Convert User object to dict and flatten for onboarding service
            user_dict = user.dict() if hasattr(user, 'dict') else user.__dict__
            profile = user_dict.get("profile", {})
            personality = user_dict.get("personality", {})
            
            return {
                "user_id": str(user_dict.get("_id", user_id)),
                "email": user_dict.get("email"),
                "username": user_dict.get("username"),
                # Profile fields
                "first_name": profile.get("first_name"),
                "last_name": profile.get("last_name"), 
                "phone": profile.get("phone"),
                "avatar_url": profile.get("avatar_url"),
                "date_of_birth": profile.get("date_of_birth"),
                "occupation": profile.get("occupation"),
                "company": profile.get("company"),
                "industry": profile.get("industry"),
                "position_level": profile.get("position_level"),
                "work_location": profile.get("work_location"),
                # Personality fields
                "personality": personality,
                "interests": profile.get("interests", []),
                "timezone": personality.get("timezone", "UTC"),
                "language_preference": personality.get("language_preference", "en"),
                "custom_instructions": personality.get("custom_instructions"),
                # Onboarding fields
                "is_onboarding_completed": profile.get("is_onboarding_completed", False),
                "onboarding_step": profile.get("onboarding_step", 0),
                "completed_steps": profile.get("completed_steps", []),
                "onboarding_started_at": profile.get("onboarding_started_at"),
                "onboarding_completed_at": profile.get("onboarding_completed_at"),
                "skip_onboarding": profile.get("skip_onboarding", False),
                # System fields
                "created_at": user_dict.get("created_at"),
                "updated_at": user_dict.get("updated_at"),
                "is_active": user_dict.get("is_active", True)
            }
            
        except Exception as e:
            traceback.print_exc()
            return None
    
    async def update_user_profile(self, user_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Update user profile using UserRepository with proper field mapping"""
        try:
            # Validate required fields
            if not user_id:
                return {"success": False, "error": "User ID is required"}
            
            # Prepare update data according to UserRepository's expected format
            profile_updates = {}
            personality_updates = {}
            root_updates = {}
            
            # Map fields to their proper locations
            profile_fields = {
                "first_name", "last_name", "phone", "avatar_url", "date_of_birth",
                "occupation", "company", "industry", "position_level", "work_location",
                "interests", "is_onboarding_completed", "onboarding_step", "completed_steps",
                "onboarding_started_at", "onboarding_completed_at", "skip_onboarding"
            }
            
            personality_fields = {
                "work_style", "communication_style", "interaction_preference",
                "preferred_tone", "working_hours", "break_style", "primary_goals",
                "task_priorities", "planning_horizon", "success_metrics",
                "motivation_factors", "learning_style", "stress_management",
                "reminder_style", "feedback_preference", "privacy_level",
                "device_usage", "tech_level", "notification_preferences",
                "timezone", "language_preference", "custom_instructions"
            }
            
            # Separate updates by location
            for key, value in updates.items():
                if key == "personality" and isinstance(value, dict):
                    # Handle nested personality object update
                    personality_updates.update(value)
                elif key in profile_fields:
                    profile_updates[key] = value
                elif key in personality_fields:
                    personality_updates[key] = value
                elif key in ["email", "username", "is_active", "is_verified"]:
                    root_updates[key] = value
            
            # Create UserUpdate object for the repository
            from app.models.user import UserUpdate, UserPersonality
            
            # Prepare update data
            update_fields = {}
            update_fields.update(profile_updates)
            update_fields.update(root_updates)
            
            # Handle personality updates
            if personality_updates:
                personality_update = UserPersonality(**personality_updates)
                update_fields["personality"] = personality_update
            
            update_data = UserUpdate(**update_fields)
            
            # Perform the update
            updated_user = self.user_repository.update_user(user_id, update_data)
            
            if updated_user:
                return {
                    "success": True,
                    "user_id": user_id,
                    "updates_applied": list(updates.keys()),
                    "message": "User profile updated successfully"
                }
            else:
                return {
                    "success": False,
                    "error": "Failed to update user profile - user not found or no changes made"
                }
            
        except Exception as e:
            traceback.print_exc()
            return {
                "success": False,
                "error": f"Failed to update user profile: {str(e)}"
            }
    
    def get_user_by_id(self, user_id: str):
        """Get user by ID using repository"""
        return self.user_repository.get_user_by_id(user_id)
    
    def get_user_by_username(self, username: str):
        """Get user by username using repository"""
        return self.user_repository.get_user_by_username(username)
    
    def get_user_by_email(self, email: str):
        """Get user by email using repository"""
        return self.user_repository.get_user_by_email(email)