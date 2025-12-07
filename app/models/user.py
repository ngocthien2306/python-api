from pydantic import BaseModel, EmailStr, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
from bson import ObjectId
from app.utils.timezone_helper import local_now

class UserPersonality(BaseModel):
    communication_style: Optional[str] = "friendly"  # friendly, formal, casual, professional
    preferred_tone: Optional[str] = "helpful"       # helpful, assertive, encouraging, direct
    interaction_preference: Optional[str] = "detailed"  # brief, detailed, interactive
    work_style: Optional[str] = "organized"         # organized, flexible, deadline-driven, creative
    interests: List[str] = []                       # user interests for context
    timezone: Optional[str] = "UTC"                 # user timezone
    language_preference: Optional[str] = "en"       # language preference
    custom_instructions: Optional[str] = None       # custom ChatGPT instructions
    # Extended personality fields for onboarding
    working_hours: Optional[str] = None
    break_style: Optional[str] = None
    primary_goals: List[str] = []
    task_priorities: Optional[str] = None
    planning_horizon: Optional[str] = None
    success_metrics: List[str] = []
    motivation_factors: List[str] = []
    learning_style: Optional[str] = None
    stress_management: List[str] = []
    reminder_style: Optional[str] = None
    feedback_preference: Optional[str] = None
    privacy_level: Optional[str] = None
    device_usage: Optional[str] = None
    tech_level: Optional[str] = None
    notification_preferences: List[str] = []

class UserProfile(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
    avatar_url: Optional[str] = None
    date_of_birth: Optional[str] = None
    occupation: Optional[str] = None
    company: Optional[str] = None
    # Extended profile fields for onboarding
    industry: Optional[str] = None
    position_level: Optional[str] = None
    work_location: Optional[str] = None
    interests: List[str] = []
    # Onboarding status fields
    is_onboarding_completed: bool = False
    onboarding_step: int = 0
    completed_steps: List[int] = []
    onboarding_started_at: Optional[str] = None
    onboarding_completed_at: Optional[str] = None
    skip_onboarding: bool = False

class User(BaseModel):
    id: Optional[str] = Field(default=None, alias="_id")
    email: EmailStr
    username: str
    hashed_password: str
    is_active: bool = True
    is_verified: bool = False
    is_admin: bool = False
    profile: UserProfile = UserProfile()
    personality: UserPersonality = UserPersonality()
    created_at: datetime = Field(default_factory=local_now)
    updated_at: datetime = Field(default_factory=local_now)
    last_login: Optional[datetime] = None
    push_subscriptions: List[Dict[str, Any]] = []
    
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
    # Extended profile fields
    industry: Optional[str] = None
    position_level: Optional[str] = None
    work_location: Optional[str] = None
    interests: Optional[List[str]] = None
    # Onboarding fields
    is_onboarding_completed: Optional[bool] = None
    onboarding_step: Optional[int] = None
    completed_steps: Optional[List[int]] = None
    onboarding_started_at: Optional[str] = None
    onboarding_completed_at: Optional[str] = None
    skip_onboarding: Optional[bool] = None
    # Personality
    personality: Optional[UserPersonality] = None

# Create alias for backward compatibility
PersonalityUpdate = UserPersonality

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
    is_admin: bool = False
    profile: UserProfile
    personality: UserPersonality
    created_at: datetime
    last_login: Optional[datetime] = None