from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from datetime import datetime

class OnboardingProfileData(BaseModel):
    # Professional Info
    occupation: Optional[str] = None
    company: Optional[str] = None
    industry: Optional[str] = None
    position_level: Optional[str] = None
    work_location: Optional[str] = None
    
    # Work Style
    work_style: Optional[str] = "organized"  # organized, flexible, creative, analytical
    communication_style: Optional[str] = "friendly"  # friendly, professional, direct
    working_hours: Optional[str] = None
    break_style: Optional[str] = None
    
    # Goals & Priorities
    primary_goals: List[str] = []
    task_priorities: Optional[str] = None
    planning_horizon: Optional[str] = None
    success_metrics: List[str] = []
    
    # Personal Interests
    interests: List[str] = []
    learning_style: Optional[str] = None
    motivation_factors: List[str] = []
    stress_management: List[str] = []
    
    # Tech Settings
    timezone: Optional[str] = "UTC"
    language_preference: Optional[str] = "en"
    notification_preferences: List[str] = []
    device_usage: Optional[str] = None
    tech_level: Optional[str] = None
    
    # AI Customization
    interaction_preference: Optional[str] = "detailed"  # detailed, concise, conversational
    custom_instructions: Optional[str] = None
    reminder_style: Optional[str] = None
    feedback_preference: Optional[str] = None
    privacy_level: Optional[str] = None

class OnboardingRequest(BaseModel):
    user_id: str
    onboarding_data: OnboardingProfileData
    completed_at: Optional[str] = None

class OnboardingResponse(BaseModel):
    success: bool
    user_id: Optional[str] = None
    message: Optional[str] = None
    error: Optional[str] = None
    updated_profile: Optional[Dict[str, Any]] = None

class OnboardingStatus(BaseModel):
    user_id: str
    is_onboarding_completed: bool = False
    onboarding_step: int = 0
    completed_steps: List[int] = []
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    skip_onboarding: bool = False

class UserPersonalizationProfile(BaseModel):
    """Extended user profile with personalization data"""
    # Basic Profile
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
    avatar_url: Optional[str] = None
    date_of_birth: Optional[str] = None
    
    # Professional Info (from onboarding)
    occupation: Optional[str] = None
    company: Optional[str] = None
    industry: Optional[str] = None
    position_level: Optional[str] = None
    work_location: Optional[str] = None
    
    # Personality & Preferences
    work_style: Optional[str] = "organized"
    communication_style: Optional[str] = "friendly"
    interaction_preference: Optional[str] = "detailed"
    preferred_tone: Optional[str] = "helpful"
    working_hours: Optional[str] = None
    break_style: Optional[str] = None
    
    # Goals & Motivation
    primary_goals: List[str] = []
    task_priorities: Optional[str] = None
    planning_horizon: Optional[str] = None
    success_metrics: List[str] = []
    motivation_factors: List[str] = []
    
    # Learning & Growth
    interests: List[str] = []
    learning_style: Optional[str] = None
    stress_management: List[str] = []
    
    # Technical Preferences
    timezone: Optional[str] = "UTC"
    language_preference: Optional[str] = "en"
    notification_preferences: List[str] = []
    device_usage: Optional[str] = None
    tech_level: Optional[str] = None
    
    # AI Assistant Settings
    custom_instructions: Optional[str] = None
    reminder_style: Optional[str] = None
    feedback_preference: Optional[str] = None
    privacy_level: Optional[str] = None
    
    # Onboarding Status
    is_onboarding_completed: bool = False
    onboarding_completed_at: Optional[datetime] = None