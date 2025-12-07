from pydantic import BaseModel, Field, EmailStr
from datetime import datetime
from typing import Optional
from bson import ObjectId


class AdminUser(BaseModel):
    """Model for admin users - separate from regular users"""
    id: Optional[str] = Field(None, alias="_id")
    email: EmailStr
    username: str
    password_hash: str
    full_name: Optional[str] = None
    role: str = "admin"  # admin, super_admin
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    last_login: Optional[datetime] = None
    permissions: list[str] = Field(default_factory=lambda: ["view", "edit", "delete"])
    
    class Config:
        populate_by_name = True
        json_encoders = {
            ObjectId: str,
            datetime: lambda v: v.isoformat()
        }


class AdminUserCreate(BaseModel):
    """Schema for creating admin user"""
    email: EmailStr
    username: str
    password: str
    full_name: Optional[str] = None
    role: str = "admin"
    permissions: list[str] = ["view", "edit", "delete"]


class AdminUserResponse(BaseModel):
    """Schema for admin user response"""
    id: str = Field(..., alias="_id")
    email: str
    username: str
    full_name: Optional[str] = None
    role: str
    is_active: bool
    created_at: datetime
    last_login: Optional[datetime] = None
    permissions: list[str]
    
    class Config:
        populate_by_name = True
        json_encoders = {
            ObjectId: str,
            datetime: lambda v: v.isoformat()
        }


class AdminLoginRequest(BaseModel):
    """Schema for admin login"""
    username: str
    password: str


class AdminTokenResponse(BaseModel):
    """Schema for admin token response"""
    access_token: str
    token_type: str = "bearer"
    admin: AdminUserResponse
