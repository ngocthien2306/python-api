from fastapi import APIRouter, Depends, HTTPException
from app.core.auth import get_current_user_token
from app.models.user import TokenData
from app.core.dependencies import get_database_manager
from app.schemas.user_onboarding import (
    OnboardingRequest, 
    OnboardingResponse, 
    OnboardingStatus,
    UserPersonalizationProfile
)
from app.services.user_onboarding_service import UserOnboardingService

router = APIRouter()

@router.post("/complete", response_model=OnboardingResponse)
async def complete_onboarding(
    request: OnboardingRequest,
    db_manager = Depends(get_database_manager),
    current_user_token: TokenData = Depends(get_current_user_token)
):
    """Complete user onboarding with personalization data"""
    try:
        onboarding_service = UserOnboardingService(db_manager)
        result = await onboarding_service.complete_onboarding(
            user_id=request.user_id,
            onboarding_data=request.onboarding_data,
            completed_at=request.completed_at
        )
        
        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error"))
        
        return OnboardingResponse(
            success=True,
            user_id=request.user_id,
            message="Onboarding completed successfully",
            updated_profile=result.get("updated_profile")
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/status/{user_id}", response_model=OnboardingStatus)
async def get_onboarding_status(
    user_id: str,
    db_manager = Depends(get_database_manager),
    current_user_token: TokenData = Depends(get_current_user_token)
):
    """Get user's onboarding status"""
    try:
        onboarding_service = UserOnboardingService(db_manager)
        status = await onboarding_service.get_onboarding_status(user_id)
        
        return OnboardingStatus(**status)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/skip/{user_id}")
async def skip_onboarding(
    user_id: str,
    db_manager = Depends(get_database_manager),
    current_user_token: TokenData = Depends(get_current_user_token)
):
    """Mark onboarding as skipped for user"""
    try:
        onboarding_service = UserOnboardingService(db_manager)
        result = await onboarding_service.skip_onboarding(user_id)
        
        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error"))
        
        return {"success": True, "message": "Onboarding skipped successfully"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/profile/{user_id}", response_model=UserPersonalizationProfile)
async def get_personalization_profile(
    user_id: str,
    db_manager = Depends(get_database_manager),
    current_user_token: TokenData = Depends(get_current_user_token)
):
    """Get user's complete personalization profile"""
    try:
        onboarding_service = UserOnboardingService(db_manager)
        profile = await onboarding_service.get_personalization_profile(user_id)
        
        if not profile:
            raise HTTPException(status_code=404, detail="User profile not found")
        
        return UserPersonalizationProfile(**profile)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/profile/{user_id}", response_model=OnboardingResponse)
async def update_personalization_profile(
    user_id: str,
    profile_data: UserPersonalizationProfile,
    db_manager = Depends(get_database_manager),
    current_user_token: TokenData = Depends(get_current_user_token)
):
    """Update user's personalization profile"""
    try:
        onboarding_service = UserOnboardingService(db_manager)
        result = await onboarding_service.update_personalization_profile(
            user_id=user_id,
            profile_data=profile_data.dict(exclude_unset=True)
        )
        
        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error"))
        
        return OnboardingResponse(
            success=True,
            user_id=user_id,
            message="Profile updated successfully",
            updated_profile=result.get("updated_profile")
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))