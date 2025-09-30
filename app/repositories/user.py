from typing import Optional, Dict, Any
from datetime import datetime
from pymongo.collection import Collection
from app.models.user import User, UserCreate, UserUpdate
from app.core.auth import get_password_hash
from bson import ObjectId

class UserRepository:
    def __init__(self, db):
        self.collection: Collection = db.users
        
    def create_user(self, user_data: UserCreate) -> Optional[User]:
        """Create a new user."""
        try:
            # Check if user exists
            if self.get_user_by_username(user_data.username) or self.get_user_by_email(user_data.email):
                return None
            
            user_dict = {
                "email": user_data.email,
                "username": user_data.username,
                "hashed_password": get_password_hash(user_data.password),
                "is_active": True,
                "is_verified": False,
                "profile": {
                    "first_name": user_data.first_name,
                    "last_name": user_data.last_name,
                    "phone": None,
                    "avatar_url": None,
                    "date_of_birth": None,
                    "occupation": None,
                    "company": None,
                    # Extended profile fields for onboarding
                    "industry": None,
                    "position_level": None,
                    "work_location": None,
                    "interests": [],
                    # Onboarding status fields
                    "is_onboarding_completed": False,
                    "onboarding_step": 0,
                    "completed_steps": [],
                    "onboarding_started_at": None,
                    "onboarding_completed_at": None,
                    "skip_onboarding": False
                },
                "personality": {
                    "communication_style": "friendly",
                    "preferred_tone": "helpful", 
                    "interaction_preference": "detailed",
                    "work_style": "organized",
                    "interests": [],
                    "timezone": "UTC",
                    "language_preference": "en",
                    "custom_instructions": None,
                    # Extended personality fields for onboarding
                    "working_hours": None,
                    "break_style": None,
                    "primary_goals": [],
                    "task_priorities": None,
                    "planning_horizon": None,
                    "success_metrics": [],
                    "motivation_factors": [],
                    "learning_style": None,
                    "stress_management": [],
                    "reminder_style": None,
                    "feedback_preference": None,
                    "privacy_level": None,
                    "device_usage": None,
                    "tech_level": None,
                    "notification_preferences": []
                },
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
                "last_login": None,
                "push_subscriptions": []
            }
            
            result = self.collection.insert_one(user_dict)
            user_dict["_id"] = str(result.inserted_id)
            return User(**user_dict)
            
        except Exception as e:
            print(f"Error creating user: {str(e)}")
            return None
    
    def get_user_by_username(self, username: str) -> Optional[User]:
        """Get user by username."""
        try:
            user_doc = self.collection.find_one({"username": username})
            if user_doc:
                user_doc["_id"] = str(user_doc["_id"])
                return User(**user_doc)
            return None
        except Exception as e:
            print(f"Error getting user by username: {str(e)}")
            return None
    
    def get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email."""
        try:
            user_doc = self.collection.find_one({"email": email})
            if user_doc:
                user_doc["_id"] = str(user_doc["_id"])
                return User(**user_doc)
            return None
        except Exception as e:
            print(f"Error getting user by email: {str(e)}")
            return None
    
    def get_user_by_id(self, user_id: str) -> Optional[User]:
        """Get user by ID."""
        try:
            user_doc = self.collection.find_one({"_id": ObjectId(user_id)})
            if user_doc:
                user_doc["_id"] = str(user_doc["_id"])
                return User(**user_doc)
            return None
        except Exception as e:
            print(f"Error getting user by ID: {str(e)}")
            return None
    
    def update_user(self, user_id: str, user_data: UserUpdate) -> Optional[User]:
        """Update user information."""
        try:
            update_data = {}
            
            # Update profile fields - Basic fields
            if user_data.first_name is not None:
                update_data["profile.first_name"] = user_data.first_name
            if user_data.last_name is not None:
                update_data["profile.last_name"] = user_data.last_name
            if user_data.phone is not None:
                update_data["profile.phone"] = user_data.phone
            if user_data.avatar_url is not None:
                update_data["profile.avatar_url"] = user_data.avatar_url
            if user_data.date_of_birth is not None:
                update_data["profile.date_of_birth"] = user_data.date_of_birth
            if user_data.occupation is not None:
                update_data["profile.occupation"] = user_data.occupation
            if user_data.company is not None:
                update_data["profile.company"] = user_data.company
            
            # Update profile fields - Extended fields
            if user_data.industry is not None:
                update_data["profile.industry"] = user_data.industry
            if user_data.position_level is not None:
                update_data["profile.position_level"] = user_data.position_level
            if user_data.work_location is not None:
                update_data["profile.work_location"] = user_data.work_location
            if user_data.interests is not None:
                update_data["profile.interests"] = user_data.interests
            
            # Update profile fields - Onboarding status
            if user_data.is_onboarding_completed is not None:
                update_data["profile.is_onboarding_completed"] = user_data.is_onboarding_completed
            if user_data.onboarding_step is not None:
                update_data["profile.onboarding_step"] = user_data.onboarding_step
            if user_data.completed_steps is not None:
                update_data["profile.completed_steps"] = user_data.completed_steps
            if user_data.onboarding_started_at is not None:
                update_data["profile.onboarding_started_at"] = user_data.onboarding_started_at
            if user_data.onboarding_completed_at is not None:
                update_data["profile.onboarding_completed_at"] = user_data.onboarding_completed_at
            if user_data.skip_onboarding is not None:
                update_data["profile.skip_onboarding"] = user_data.skip_onboarding
            
            # Update personality fields
            if user_data.personality is not None:
                personality_dict = user_data.personality.model_dump()
                for key, value in personality_dict.items():
                    if value is not None:
                        update_data[f"personality.{key}"] = value
            
            update_data["updated_at"] = datetime.utcnow()
            
            result = self.collection.update_one(
                {"_id": ObjectId(user_id)},
                {"$set": update_data}
            )
            
            if result.modified_count > 0:
                return self.get_user_by_id(user_id)
            return None
            
        except Exception as e:
            print(f"Error updating user: {str(e)}")
            return None
    
    def update_last_login(self, user_id: str) -> bool:
        """Update user's last login timestamp."""
        try:
            result = self.collection.update_one(
                {"_id": ObjectId(user_id)},
                {"$set": {"last_login": datetime.utcnow()}}
            )
            return result.modified_count > 0
        except Exception as e:
            print(f"Error updating last login: {str(e)}")
            return False
    
    def authenticate_user(self, username: str, password: str) -> Optional[User]:
        """Authenticate user with username and password."""
        from app.core.auth import verify_password
        
        user = self.get_user_by_username(username)
        if not user:
            return None
        if not verify_password(password, user.hashed_password):
            return None
        return user
    
    def add_push_subscription(self, user_id: str, subscription_data: Dict[str, Any]) -> bool:
        """Add a push subscription for the user."""
        try:
            result = self.collection.update_one(
                {"_id": ObjectId(user_id)},
                {"$push": {"push_subscriptions": subscription_data}}
            )
            return result.modified_count > 0
        except Exception as e:
            print(f"Error adding push subscription: {str(e)}")
            return False
    
    def remove_push_subscription(self, user_id: str, endpoint: str) -> bool:
        """Remove a push subscription by endpoint."""
        try:
            result = self.collection.update_one(
                {"_id": ObjectId(user_id)},
                {"$pull": {"push_subscriptions": {"endpoint": endpoint}}}
            )
            return result.modified_count > 0
        except Exception as e:
            print(f"Error removing push subscription: {str(e)}")
            return False
    
    def get_user_push_subscriptions(self, user_id: str) -> list:
        """Get all push subscriptions for a user."""
        try:
            user_doc = self.collection.find_one(
                {"_id": ObjectId(user_id)},
                {"push_subscriptions": 1}
            )
            if user_doc:
                return user_doc.get("push_subscriptions", [])
            return []
        except Exception as e:
            print(f"Error getting push subscriptions: {str(e)}")
            return []
    
    def verify_user_email(self, user_id: str) -> bool:
        """Mark user email as verified."""
        try:
            result = self.collection.update_one(
                {"_id": ObjectId(user_id)},
                {"$set": {"is_verified": True, "updated_at": datetime.utcnow()}}
            )
            return result.modified_count > 0
        except Exception as e:
            print(f"Error verifying user email: {str(e)}")
            return False
    
    def update_user_password(self, user_id: str, new_password: str) -> bool:
        """Update user password."""
        try:
            hashed_password = get_password_hash(new_password)
            result = self.collection.update_one(
                {"_id": ObjectId(user_id)},
                {"$set": {"hashed_password": hashed_password, "updated_at": datetime.utcnow()}}
            )
            return result.modified_count > 0
        except Exception as e:
            print(f"Error updating user password: {str(e)}")
            return False