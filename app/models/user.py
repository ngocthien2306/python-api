from pydantic import BaseModel, EmailStr, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
from bson import ObjectId

class UserPersonality(BaseModel):
    communication_style: Optional[str] = "friendly"  # friendly, formal, casual, professional
    preferred_tone: Optional[str] = "helpful"       # helpful, assertive, encouraging, direct
    interaction_preference: Optional[str] = "detailed"  # brief, detailed, interactive
    work_style: Optional[str] = "organized"         # organized, flexible, deadline-driven, creative
    interests: List[str] = []                       # user interests for context
    timezone: Optional[str] = "UTC"                 # user timezone
    language_preference: Optional[str] = "en"       # language preference
    custom_instructions: Optional[str] = None       # custom ChatGPT instructions

class UserProfile(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
    avatar_url: Optional[str] = None
    date_of_birth: Optional[str] = None
    occupation: Optional[str] = None
    company: Optional[str] = None

class User(BaseModel):
    id: Optional[str] = Field(default=None, alias="_id")
    email: EmailStr
    username: str
    hashed_password: str
    is_active: bool = True
    is_verified: bool = False
    profile: UserProfile = UserProfile()
    personality: UserPersonality = UserPersonality()
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    last_login: Optional[datetime] = None
    
    class Config:
        populate_by_name = True
        json_encoders = {
            ObjectId: str,
            datetime: lambda v: v.isoformat()
        }

class UserCreate(BaseModel):
    email: EmailStr
    username: str
    password: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None

class UserUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
    avatar_url: Optional[str] = None
    date_of_birth: Optional[str] = None
    occupation: Optional[str] = None
    company: Optional[str] = None
    personality: Optional[UserPersonality] = None

class UserLogin(BaseModel):
    username: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None

class UserResponse(BaseModel):
    id: str
    email: str
    username: str
    is_active: bool
    profile: UserProfile
    personality: UserPersonality
    created_at: datetime
    last_login: Optional[datetime] = None