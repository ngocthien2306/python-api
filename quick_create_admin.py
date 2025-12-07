#!/usr/bin/env python3
"""Quick test script to create admin user"""
import sys
sys.path.append('.')

from app.core.database import init_database
from app.repositories.admin_user_repository import AdminUserRepository
from app.models.admin_user import AdminUserCreate

# Initialize database
print("Connecting to database...")
db = init_database()
print(f"Database connected: {db.name}")

# Create repository
admin_repo = AdminUserRepository(db)
print("Repository created")

# Create admin user
print("\nCreating admin user...")
admin_data = AdminUserCreate(
    email="admin@example.com",
    username="admin",
    password="admin123",
    full_name="Admin User",
    role="super_admin",
    permissions=["view", "edit", "delete"]
)

try:
    admin = admin_repo.create_admin_user(admin_data)
    print(f"\n✅ Admin user created successfully!")
    print(f"   Username: {admin.username}")
    print(f"   Email: {admin.email}")
    print(f"   Role: {admin.role}")
except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()
