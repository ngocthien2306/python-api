from typing import Optional, List
from datetime import datetime
from bson import ObjectId
from pymongo.database import Database

from app.models.admin_user import AdminUser, AdminUserCreate
from app.core.auth import get_password_hash


class AdminUserRepository:
    """Repository for admin users operations"""
    
    def __init__(self, db: Database):
        self.collection = db.admin_users
        self._ensure_indexes()
    
    def _ensure_indexes(self):
        """Create indexes for admin users collection"""
        self.collection.create_index("email", unique=True)
        self.collection.create_index("username", unique=True)
    
    def create_admin_user(self, admin_data: AdminUserCreate) -> AdminUser:
        """Create new admin user (synchronous for CLI)"""
        password_hash = get_password_hash(admin_data.password)
        
        admin_dict = {
            "email": admin_data.email,
            "username": admin_data.username,
            "password_hash": password_hash,
            "full_name": admin_data.full_name,
            "role": admin_data.role,
            "permissions": admin_data.permissions,
            "is_active": True,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "last_login": None
        }
        
        result = self.collection.insert_one(admin_dict)
        admin_dict["_id"] = str(result.inserted_id)
        
        return AdminUser(**admin_dict)
    
    def find_by_username(self, username: str) -> Optional[AdminUser]:
        """Find admin by username"""
        admin = self.collection.find_one({"username": username})
        if admin:
            admin["_id"] = str(admin["_id"])
            return AdminUser(**admin)
        return None
    
    def find_by_email(self, email: str) -> Optional[AdminUser]:
        """Find admin by email"""
        admin = self.collection.find_one({"email": email})
        if admin:
            admin["_id"] = str(admin["_id"])
            return AdminUser(**admin)
        return None
    
    def find_by_id(self, admin_id: str) -> Optional[AdminUser]:
        """Find admin by ID"""
        try:
            admin = self.collection.find_one({"_id": ObjectId(admin_id)})
            if admin:
                admin["_id"] = str(admin["_id"])
                return AdminUser(**admin)
        except Exception:
            pass
        return None
    
    def update_last_login(self, admin_id: str):
        """Update last login timestamp"""
        try:
            self.collection.update_one(
                {"_id": ObjectId(admin_id)},
                {"$set": {"last_login": datetime.utcnow()}}
            )
        except Exception:
            pass
    
    def list_all_admins(self) -> List[AdminUser]:
        """List all admin users"""
        admins = []
        for admin in self.collection.find():
            admin["_id"] = str(admin["_id"])
            admins.append(AdminUser(**admin))
        return admins
    
    def update_admin_status(self, admin_id: str, is_active: bool) -> bool:
        """Update admin active status"""
        try:
            result = self.collection.update_one(
                {"_id": ObjectId(admin_id)},
                {"$set": {"is_active": is_active, "updated_at": datetime.utcnow()}}
            )
            return result.modified_count > 0
        except Exception:
            return False
