from pymongo import MongoClient
from app.core.config import settings
from typing import Optional

class Database:
    client: Optional[MongoClient] = None
    database = None

db = Database()

def get_database():
    return db.database

def init_database():
    if settings.is_production():
        db.client = MongoClient(
            settings.MONGODB_URL,
            tls=True,
            tlsAllowInvalidCertificates=True,
            serverSelectionTimeoutMS=5000,
            connectTimeoutMS=10000,
            socketTimeoutMS=10000
        )
    else:
        db.client = MongoClient(
            settings.MONGODB_URL,
            serverSelectionTimeoutMS=5000,
            connectTimeoutMS=10000,
            socketTimeoutMS=10000
        )
    
    db.database = db.client[settings.DATABASE_NAME]
    
    # Create indexes for existing collections
    db.database.tasks.create_index([("userId", 1), ("status", 1)])
    db.database.tasks.create_index([("userId", 1), ("dueDate", 1), ("dueTime", 1)])
    db.database.conversations.create_index([("userId", 1), ("sessionId", 1)])
    db.database.reminders.create_index([("userId", 1), ("triggerTime", 1)])
    db.database.schedules.create_index([("userId", 1), ("date", 1)])
    
    # Create indexes for users collection
    db.database.users.create_index([("username", 1)], unique=True)
    db.database.users.create_index([("email", 1)], unique=True)
    db.database.users.create_index([("created_at", 1)])
    db.database.users.create_index([("is_active", 1)])
    
    # Create indexes for subscription collections
    db.database.subscriptions.create_index([("user_id", 1)], unique=True)
    db.database.subscriptions.create_index([("user_id", 1), ("status", 1)])
    db.database.subscriptions.create_index([("plan_type", 1)])
    db.database.subscriptions.create_index([("end_date", 1)])
    db.database.subscriptions.create_index([("created_at", 1)])
    
    # Create indexes for usage logs
    db.database.usage_logs.create_index([("user_id", 1), ("timestamp", -1)])
    db.database.usage_logs.create_index([("user_id", 1), ("request_type", 1)])
    db.database.usage_logs.create_index([("timestamp", -1)])
    db.database.usage_logs.create_index([("session_id", 1)])

def close_database():
    if db.client:
        db.client.close()