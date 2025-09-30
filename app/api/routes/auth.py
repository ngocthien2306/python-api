from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
from app.models.user import UserCreate, UserLogin, UserUpdate, UserResponse, Token, TokenData
from app.repositories.user import UserRepository
from app.services.auth_service import AuthService
from app.core.auth import create_access_token, get_current_user_token
from app.core.database import get_database
from app.core.config import settings

router = APIRouter()

def get_user_repository():
    """Dependency to get user repository."""
    db = get_database()
    return UserRepository(db)

def get_auth_service(user_repo: UserRepository = Depends(get_user_repository)):
    """Dependency to get auth service."""
    return AuthService(user_repo)

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

@router.post("/register", response_model=dict)
async def register(
    user_data: UserCreate,
    user_repo: UserRepository = Depends(get_user_repository),
    auth_service: AuthService = Depends(get_auth_service)
):
    """Register a new user and send verification email."""
    try:
        user = user_repo.create_user(user_data)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username or email already exists"
            )
        
        # Send verification email
        email_sent = await auth_service.send_verification_email(user)
        
        return {
            "message": "User registered successfully",
            "user_id": user.id,
            "email_sent": email_sent,
            "note": "Please check your email to verify your account"
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Registration failed: {str(e)}"
        )

@router.post("/login", response_model=Token)
async def login(
    user_credentials: UserLogin,
    user_repo: UserRepository = Depends(get_user_repository)
):
    """Login user and return JWT token."""
    try:
        user = user_repo.authenticate_user(user_credentials.username, user_credentials.password)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Inactive user"
            )
        
        if not user.is_verified:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Email not verified. Please check your email and verify your account."
            )
        
        # Update last login
        user_repo.update_last_login(user.id)
        
        # Create access token
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": user.username}, expires_delta=access_token_expires
        )
        
        return Token(access_token=access_token, token_type="bearer")
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Login failed: {str(e)}"
        )

@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user = Depends(get_current_user)):
    """Get current user information."""
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        username=current_user.username,
        is_active=current_user.is_active,
        profile=current_user.profile,
        personality=current_user.personality,
        created_at=current_user.created_at,
        last_login=current_user.last_login
    )

@router.put("/me", response_model=UserResponse)
async def update_current_user(
    user_data: UserUpdate,
    current_user = Depends(get_current_user),
    user_repo: UserRepository = Depends(get_user_repository)
):
    """Update current user information."""
    try:
        updated_user = user_repo.update_user(current_user.id, user_data)
        if not updated_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to update user"
            )
        
        return UserResponse(
            id=updated_user.id,
            email=updated_user.email,
            username=updated_user.username,
            is_active=updated_user.is_active,
            profile=updated_user.profile,
            personality=updated_user.personality,
            created_at=updated_user.created_at,
            last_login=updated_user.last_login
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Update failed: {str(e)}"
        )

@router.get("/personality", response_model=dict)
async def get_user_personality(current_user = Depends(get_current_user)):
    """Get user personality settings for ChatGPT integration."""
    personality = current_user.personality
    
    # Format personality data for ChatGPT context
    chatgpt_context = {
        "user_id": current_user.id,
        "username": current_user.username,
        "personality": {
            "communication_style": personality.communication_style,
            "preferred_tone": personality.preferred_tone,
            "interaction_preference": personality.interaction_preference,
            "work_style": personality.work_style,
            "interests": personality.interests,
            "timezone": personality.timezone,
            "language_preference": personality.language_preference,
            "custom_instructions": personality.custom_instructions
        },
        "profile_context": {
            "name": f"{current_user.profile.first_name} {current_user.profile.last_name}".strip() or current_user.username,
            "occupation": current_user.profile.occupation,
            "company": current_user.profile.company
        }
    }
    
    return chatgpt_context

# Email verification schemas
class VerifyEmailRequest(BaseModel):
    token: str

class ResendVerificationRequest(BaseModel):
    email: str

class ForgotPasswordRequest(BaseModel):
    email: str

class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str

@router.post("/verify-email", response_model=dict)
async def verify_email(
    request: VerifyEmailRequest,
    auth_service: AuthService = Depends(get_auth_service)
):
    """Verify user email with token."""
    try:
        success = auth_service.verify_user_email(request.token)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired verification token"
            )
        
        return {"message": "Email verified successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Email verification failed: {str(e)}"
        )

@router.post("/resend-verification", response_model=dict)
async def resend_verification(
    request: ResendVerificationRequest,
    user_repo: UserRepository = Depends(get_user_repository),
    auth_service: AuthService = Depends(get_auth_service)
):
    """Resend verification email."""
    try:
        user = user_repo.get_user_by_email(request.email)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        if user.is_verified:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already verified"
            )
        
        email_sent = await auth_service.send_verification_email(user)
        
        return {
            "message": "Verification email sent",
            "email_sent": email_sent
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to resend verification: {str(e)}"
        )

@router.post("/forgot-password", response_model=dict)
async def forgot_password(
    request: ForgotPasswordRequest,
    auth_service: AuthService = Depends(get_auth_service)
):
    """Send password reset email."""
    try:
        email_sent = await auth_service.send_password_reset_email(request.email)
        
        # Always return success to prevent email enumeration
        return {
            "message": "If an account with this email exists, a password reset link has been sent",
            "email_sent": email_sent
        }
    except Exception as e:
        # Log error but don't reveal it to prevent email enumeration
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process password reset request"
        )

@router.post("/reset-password", response_model=dict)
async def reset_password(
    request: ResetPasswordRequest,
    auth_service: AuthService = Depends(get_auth_service)
):
    """Reset password with token."""
    try:
        success = auth_service.reset_user_password(request.token, request.new_password)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired reset token"
            )
        
        return {"message": "Password reset successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Password reset failed: {str(e)}"
        )