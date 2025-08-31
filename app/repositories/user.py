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
                    "company": None
                },
                "personality": {
                    "communication_style": "friendly",
                    "preferred_tone": "helpful", 
                    "interaction_preference": "detailed",
                    "work_style": "organized",
                    "interests": [],
                    "timezone": "UTC",
                    "language_preference": "en",
                    "custom_instructions": None
                },
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
                "last_login": None
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
            
            # Update profile fields
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
            
            # Update personality fields
            if user_data.personality is not None:
                personality_dict = user_data.personality.dict()
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