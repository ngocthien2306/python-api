from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional, Dict, Any, Annotated
from datetime import datetime, timedelta
from bson import ObjectId
from app.core.database import get_database
from app.models.user import User, UserResponse
from app.models.admin_user import AdminUser
from app.models.subscription import Subscription
from app.models.payment import Payment
from app.repositories.user import UserRepository
from app.api.routes.admin_auth import get_current_admin_user
from pydantic import BaseModel

router = APIRouter()

class AdminStats(BaseModel):
    total_users: int
    active_users: int
    verified_users: int
    total_subscriptions: int
    active_subscriptions: int
    total_revenue: float
    revenue_this_month: float
    total_payments: int
    successful_payments: int
    failed_payments: int
    new_users_this_month: int
    subscription_breakdown: Dict[str, int]

class UserAdmin(BaseModel):
    id: str
    email: str
    username: str
    is_active: bool
    is_verified: bool
    is_admin: bool
    created_at: datetime
    last_login: Optional[datetime]
    subscription_status: Optional[str]
    plan_type: Optional[str]

class SubscriptionAdmin(BaseModel):
    id: str
    user_id: str
    user_email: str
    user_username: str
    plan_type: str
    status: str
    tokens_used: int
    tokens_limit: int
    requests_used: int
    requests_limit: int
    start_date: datetime
    end_date: datetime
    price: float
    payment_status: str

class PaymentAdmin(BaseModel):
    id: str
    user_id: str
    user_email: str
    user_username: str
    plan_type: str
    amount: float
    currency: str
    gateway: str
    status: str
    transaction_id: Optional[str]
    created_at: datetime
    completed_at: Optional[datetime]

def get_user_repository():
    """Dependency to get user repository."""
    db = get_database()
    return UserRepository(db)

@router.get("/dashboard/stats", response_model=AdminStats)
async def get_dashboard_stats(
    current_admin: Annotated[AdminUser, Depends(get_current_admin_user)]
):
    """Get dashboard statistics for admin."""
    db = get_database()
    
    # Calculate date ranges
    now = datetime.utcnow()
    first_day_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    # User statistics
    total_users = db.users.count_documents({})
    active_users = db.users.count_documents({"is_active": True})
    verified_users = db.users.count_documents({"is_verified": True})
    new_users_this_month = db.users.count_documents({
        "created_at": {"$gte": first_day_of_month}
    })
    
    # Subscription statistics
    total_subscriptions = db.subscriptions.count_documents({})
    active_subscriptions = db.subscriptions.count_documents({
        "status": "active",
        "end_date": {"$gte": now}
    })
    
    # Get subscription breakdown by plan type
    subscription_pipeline = [
        {"$group": {"_id": "$plan_type", "count": {"$sum": 1}}}
    ]
    subscription_breakdown_cursor = db.subscriptions.aggregate(subscription_pipeline)
    subscription_breakdown = {item["_id"]: item["count"] for item in subscription_breakdown_cursor}
    
    # Payment statistics
    total_payments = db.payments.count_documents({})
    successful_payments = db.payments.count_documents({"status": "completed"})
    failed_payments = db.payments.count_documents({"status": "failed"})
    
    # Revenue statistics
    revenue_pipeline = [
        {"$match": {"status": "completed"}},
        {"$group": {"_id": None, "total": {"$sum": "$amount"}}}
    ]
    revenue_cursor = db.payments.aggregate(revenue_pipeline)
    revenue_data = list(revenue_cursor)
    total_revenue = revenue_data[0]["total"] if revenue_data else 0
    
    # Revenue this month
    revenue_month_pipeline = [
        {"$match": {
            "status": "completed",
            "completed_at": {"$gte": first_day_of_month}
        }},
        {"$group": {"_id": None, "total": {"$sum": "$amount"}}}
    ]
    revenue_month_cursor = db.payments.aggregate(revenue_month_pipeline)
    revenue_month_data = list(revenue_month_cursor)
    revenue_this_month = revenue_month_data[0]["total"] if revenue_month_data else 0
    
    return AdminStats(
        total_users=total_users,
        active_users=active_users,
        verified_users=verified_users,
        total_subscriptions=total_subscriptions,
        active_subscriptions=active_subscriptions,
        total_revenue=total_revenue,
        revenue_this_month=revenue_this_month,
        total_payments=total_payments,
        successful_payments=successful_payments,
        failed_payments=failed_payments,
        new_users_this_month=new_users_this_month,
        subscription_breakdown=subscription_breakdown
    )

@router.get("/users", response_model=List[UserAdmin])
async def get_all_users(
    current_admin: Annotated[AdminUser, Depends(get_current_admin_user)],
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    search: Optional[str] = None,
    is_active: Optional[bool] = None,
    is_verified: Optional[bool] = None
):
    """Get all users with pagination and filters."""
    db = get_database()
    
    # Build query
    query = {}
    if search:
        query["$or"] = [
            {"email": {"$regex": search, "$options": "i"}},
            {"username": {"$regex": search, "$options": "i"}},
            {"profile.first_name": {"$regex": search, "$options": "i"}},
            {"profile.last_name": {"$regex": search, "$options": "i"}}
        ]
    if is_active is not None:
        query["is_active"] = is_active
    if is_verified is not None:
        query["is_verified"] = is_verified
    
    # Get users
    users_cursor = db.users.find(query).sort("created_at", -1).skip(skip).limit(limit)
    users = list(users_cursor)
    
    # Enrich with subscription data
    result = []
    for user in users:
        subscription = db.subscriptions.find_one({
            "user_id": str(user["_id"]),
            "status": "active",
            "end_date": {"$gte": datetime.utcnow()}
        })
        
        result.append(UserAdmin(
            id=str(user["_id"]),
            email=user["email"],
            username=user["username"],
            is_active=user.get("is_active", True),
            is_verified=user.get("is_verified", False),
            is_admin=user.get("is_admin", False),
            created_at=user.get("created_at", datetime.utcnow()),
            last_login=user.get("last_login"),
            subscription_status=subscription["status"] if subscription else None,
            plan_type=subscription["plan_type"] if subscription else None
        ))
    
    return result

@router.get("/users/{user_id}", response_model=UserResponse)
async def get_user_details(
    user_id: str,
    current_admin: Annotated[AdminUser, Depends(get_current_admin_user)]
):
    """Get detailed information about a specific user."""
    db = get_database()
    
    try:
        user = db.users.find_one({"_id": ObjectId(user_id)})
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        user["_id"] = str(user["_id"])
        return UserResponse(**user)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

class UpdateStatusRequest(BaseModel):
    is_active: bool

@router.patch("/users/{user_id}/status")
async def update_user_status(
    user_id: str,
    request: UpdateStatusRequest,
    current_admin: Annotated[AdminUser, Depends(get_current_admin_user)]
):
    """Activate or deactivate a user."""
    db = get_database()
    
    try:
        result = db.users.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": {"is_active": request.is_active, "updated_at": datetime.utcnow()}}
        )
        
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="User not found")
        
        return {"message": f"User {'activated' if request.is_active else 'deactivated'} successfully"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

class UpdateVerifyRequest(BaseModel):
    is_verified: bool

@router.patch("/users/{user_id}/verify")
async def verify_user(
    user_id: str,
    request: UpdateVerifyRequest,
    current_admin: Annotated[AdminUser, Depends(get_current_admin_user)]
):
    """Verify or unverify a user."""
    db = get_database()
    
    try:
        result = db.users.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": {"is_verified": request.is_verified, "updated_at": datetime.utcnow()}}
        )
        
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="User not found")
        
        return {"message": f"User {'verified' if request.is_verified else 'unverified'} successfully"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/users/{user_id}")
async def delete_user(
    user_id: str,
    current_admin: Annotated[AdminUser, Depends(get_current_admin_user)]
):
    """Delete a user and all related data."""
    db = get_database()
    
    try:
        # Delete user
        result = db.users.delete_one({"_id": ObjectId(user_id)})
        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Delete related data
        db.subscriptions.delete_many({"user_id": user_id})
        db.payments.delete_many({"user_id": user_id})
        db.tasks.delete_many({"user_id": user_id})
        db.reminders.delete_many({"user_id": user_id})
        db.schedules.delete_many({"user_id": user_id})
        db.conversations.delete_many({"user_id": user_id})
        
        return {"message": "User and related data deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/subscriptions", response_model=List[SubscriptionAdmin])
async def get_all_subscriptions(
    current_admin: Annotated[AdminUser, Depends(get_current_admin_user)],
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    plan_type: Optional[str] = None,
    status: Optional[str] = None
):
    """Get all subscriptions with pagination and filters."""
    db = get_database()
    
    # Build query
    query = {}
    if plan_type:
        query["plan_type"] = plan_type
    if status:
        query["status"] = status
    
    # Get subscriptions
    subscriptions_cursor = db.subscriptions.find(query).sort("created_at", -1).skip(skip).limit(limit)
    subscriptions = list(subscriptions_cursor)
    
    # Enrich with user data
    result = []
    for sub in subscriptions:
        user = db.users.find_one({"_id": ObjectId(sub["user_id"])})
        
        result.append(SubscriptionAdmin(
            id=str(sub["_id"]),
            user_id=sub["user_id"],
            user_email=user["email"] if user else "Unknown",
            user_username=user["username"] if user else "Unknown",
            plan_type=sub["plan_type"],
            status=sub["status"],
            tokens_used=sub.get("tokens_used", 0),
            tokens_limit=sub.get("tokens_limit", 0),
            requests_used=sub.get("requests_used", 0),
            requests_limit=sub.get("requests_limit", 0),
            start_date=sub["start_date"],
            end_date=sub["end_date"],
            price=sub.get("price", 0),
            payment_status=sub.get("payment_status", "pending")
        ))
    
    return result

class UpdateSubscriptionStatusRequest(BaseModel):
    status: str

@router.patch("/subscriptions/{subscription_id}/status")
async def update_subscription_status(
    subscription_id: str,
    request: UpdateSubscriptionStatusRequest,
    current_admin: Annotated[AdminUser, Depends(get_current_admin_user)]
):
    """Update subscription status."""
    db = get_database()
    
    try:
        result = db.subscriptions.update_one(
            {"_id": ObjectId(subscription_id)},
            {"$set": {"status": request.status, "updated_at": datetime.utcnow()}}
        )
        
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Subscription not found")
        
        return {"message": "Subscription status updated successfully"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/subscriptions/{subscription_id}")
async def delete_subscription(
    subscription_id: str,
    current_admin: Annotated[AdminUser, Depends(get_current_admin_user)]
):
    """Delete a subscription."""
    db = get_database()
    
    try:
        result = db.subscriptions.delete_one({"_id": ObjectId(subscription_id)})
        
        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Subscription not found")
        
        return {"message": "Subscription deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/payments", response_model=List[PaymentAdmin])
async def get_all_payments(
    current_admin: Annotated[AdminUser, Depends(get_current_admin_user)],
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    status: Optional[str] = None,
    gateway: Optional[str] = None
):
    """Get all payments with pagination and filters."""
    db = get_database()
    
    # Build query
    query = {}
    if status:
        query["status"] = status
    if gateway:
        query["gateway"] = gateway
    
    # Get payments
    payments_cursor = db.payments.find(query).sort("created_at", -1).skip(skip).limit(limit)
    payments = list(payments_cursor)
    
    # Enrich with user data
    result = []
    for payment in payments:
        user = db.users.find_one({"_id": ObjectId(payment["user_id"])})
        
        result.append(PaymentAdmin(
            id=str(payment["_id"]),
            user_id=payment["user_id"],
            user_email=user["email"] if user else "Unknown",
            user_username=user["username"] if user else "Unknown",
            plan_type=payment["plan_type"],
            amount=payment["amount"],
            currency=payment.get("currency", "VND"),
            gateway=payment["gateway"],
            status=payment["status"],
            transaction_id=payment.get("transaction_id"),
            created_at=payment["created_at"],
            completed_at=payment.get("completed_at")
        ))
    
    return result

@router.get("/payments/{payment_id}")
async def get_payment_details(
    payment_id: str,
    current_admin: Annotated[AdminUser, Depends(get_current_admin_user)]
):
    """Get detailed information about a specific payment."""
    db = get_database()
    
    try:
        payment = db.payments.find_one({"_id": ObjectId(payment_id)})
        if not payment:
            raise HTTPException(status_code=404, detail="Payment not found")
        
        payment["_id"] = str(payment["_id"])
        return payment
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
