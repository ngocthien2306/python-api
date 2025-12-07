from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Annotated

from app.models.admin_user import (
    AdminLoginRequest,
    AdminTokenResponse,
    AdminUserResponse,
    AdminUser
)
from app.repositories.admin_user_repository import AdminUserRepository
from app.core.database import get_database
from app.core.auth import verify_password, create_access_token, decode_access_token
from pymongo.database import Database

router = APIRouter(prefix="/admin-auth", tags=["Admin Authentication"])
security = HTTPBearer()


def get_admin_user_repository(db: Database = Depends(get_database)) -> AdminUserRepository:
    """Dependency to get admin user repository"""
    return AdminUserRepository(db)


async def get_current_admin_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
    admin_repo: Annotated[AdminUserRepository, Depends(get_admin_user_repository)]
) -> AdminUser:
    """Get current authenticated admin user"""
    try:
        token = credentials.credentials
        payload = decode_access_token(token)
        
        if not payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
        
        # Check if token is for admin (has admin_id instead of user_id)
        admin_id = payload.get("admin_id")
        if not admin_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Not an admin token"
            )
        
        admin = admin_repo.find_by_id(admin_id)
        if not admin:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Admin not found"
            )
        
        if not admin.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Admin account is inactive"
            )
        
        return admin
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials"
        )


@router.post("/login", response_model=AdminTokenResponse)
async def admin_login(
    login_data: AdminLoginRequest,
    admin_repo: Annotated[AdminUserRepository, Depends(get_admin_user_repository)]
):
    """Admin login endpoint - separate from user login"""
    # Find admin by username
    admin = admin_repo.find_by_username(login_data.username)
    
    if not admin:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password"
        )
    
    # Verify password
    if not verify_password(login_data.password, admin.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password"
        )
    
    # Check if admin is active
    if not admin.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Admin account is inactive"
        )
    
    # Update last login
    admin_repo.update_last_login(admin.id)
    
    # Create access token with admin_id (different from user token)
    access_token = create_access_token(data={"admin_id": admin.id, "role": admin.role})
    
    # Prepare response
    admin_response = AdminUserResponse(
        _id=admin.id,
        email=admin.email,
        username=admin.username,
        full_name=admin.full_name,
        role=admin.role,
        is_active=admin.is_active,
        created_at=admin.created_at,
        last_login=admin.last_login,
        permissions=admin.permissions
    )
    
    return AdminTokenResponse(
        access_token=access_token,
        admin=admin_response
    )


@router.get("/me", response_model=AdminUserResponse)
async def get_current_admin_info(
    current_admin: Annotated[AdminUser, Depends(get_current_admin_user)]
):
    """Get current admin user information"""
    return AdminUserResponse(
        _id=current_admin.id,
        email=current_admin.email,
        username=current_admin.username,
        full_name=current_admin.full_name,
        role=current_admin.role,
        is_active=current_admin.is_active,
        created_at=current_admin.created_at,
        last_login=current_admin.last_login,
        permissions=current_admin.permissions
    )


@router.post("/logout")
async def admin_logout(
    current_admin: Annotated[AdminUser, Depends(get_current_admin_user)]
):
    """Admin logout endpoint"""
    # In JWT, logout is handled client-side by removing the token
    return {"message": "Successfully logged out"}
