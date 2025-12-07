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
    user_firstname: Optional[str] = None
    user_lastname: Optional[str] = None
    user_phone: Optional[str] = None
    user_is_verified: bool = False
    user_is_active: bool = True
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
    user_firstname: Optional[str] = None
    user_lastname: Optional[str] = None
    user_phone: Optional[str] = None
    user_is_verified: bool = False
    user_is_active: bool = True
    plan_type: str
    amount: float
    currency: str
    gateway: str
    status: str
    transaction_id: Optional[str]
    error_message: Optional[str] = None
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
        # Handle user_id which might be stored as string (username) or ObjectId
        user = None
        user_id = sub["user_id"]
        
        try:
            # First, try to find by ObjectId (if user_id is valid ObjectId format)
            if ObjectId.is_valid(user_id):
                user = db.users.find_one({"_id": ObjectId(user_id)})
        except:
            pass
        
        # If not found, try to find by username (if user_id is a string username)
        if not user and isinstance(user_id, str):
            user = db.users.find_one({"username": user_id})
        
        result.append(SubscriptionAdmin(
            id=str(sub["_id"]),
            user_id=sub["user_id"],
            user_email=user["email"] if user else "Unknown",
            user_username=user["username"] if user else user_id if isinstance(user_id, str) else "Unknown",
            user_firstname=user.get("firstname") if user else None,
            user_lastname=user.get("lastname") if user else None,
            user_phone=user.get("phone") if user else None,
            user_is_verified=user.get("is_verified", False) if user else False,
            user_is_active=user.get("is_active", True) if user else True,
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
        # Handle user_id which might be stored as string (username) or ObjectId
        user = None
        user_id = payment["user_id"]
        
        try:
            # First, try to find by ObjectId (if user_id is valid ObjectId format)
            if ObjectId.is_valid(user_id):
                user = db.users.find_one({"_id": ObjectId(user_id)})
        except:
            pass
        
        # If not found, try to find by username (if user_id is a string username)
        if not user and isinstance(user_id, str):
            user = db.users.find_one({"username": user_id})
        
        result.append(PaymentAdmin(
            id=str(payment["_id"]),
            user_id=payment["user_id"],
            user_email=user["email"] if user else "Unknown",
            user_username=user["username"] if user else "Unknown",
            user_firstname=user.get("firstname") if user else None,
            user_lastname=user.get("lastname") if user else None,
            user_phone=user.get("phone") if user else None,
            user_is_verified=user.get("is_verified", False) if user else False,
            user_is_active=user.get("is_active", True) if user else True,
            plan_type=payment["plan_type"],
            amount=payment["amount"],
            currency=payment.get("currency", "VND"),
            gateway=payment["gateway"],
            status=payment["status"],
            transaction_id=payment.get("transaction_id"),
            error_message=payment.get("error_message"),
            created_at=payment["created_at"],
            completed_at=payment.get("completed_at")
        ))
    
    return result

@router.get("/payments/{payment_id}", response_model=PaymentAdmin)
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
        
        # Enrich with user data
        user = None
        user_id = payment["user_id"]
        
        try:
            # First, try to find by ObjectId (if user_id is valid ObjectId format)
            if ObjectId.is_valid(user_id):
                user = db.users.find_one({"_id": ObjectId(user_id)})
        except:
            pass
        
        # If not found, try to find by username (if user_id is a string username)
        if not user and isinstance(user_id, str):
            user = db.users.find_one({"username": user_id})
        
        return PaymentAdmin(
            id=str(payment["_id"]),
            user_id=payment["user_id"],
            user_email=user["email"] if user else "Unknown",
            user_username=user["username"] if user else "Unknown",
            user_firstname=user.get("firstname") if user else None,
            user_lastname=user.get("lastname") if user else None,
            user_phone=user.get("phone") if user else None,
            user_is_verified=user.get("is_verified", False) if user else False,
            user_is_active=user.get("is_active", True) if user else True,
            plan_type=payment["plan_type"],
            amount=payment["amount"],
            currency=payment.get("currency", "VND"),
            gateway=payment["gateway"],
            status=payment["status"],
            transaction_id=payment.get("transaction_id"),
            error_message=payment.get("error_message"),
            created_at=payment["created_at"],
            completed_at=payment.get("completed_at")
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# ============= CHART DATA ENDPOINTS =============

class UserGrowthData(BaseModel):
    date: str
    total_users: int
    new_users: int

class RevenueChartData(BaseModel):
    date: str
    revenue: float
    transactions: int

class SubscriptionTrendData(BaseModel):
    date: str
    free: int
    week: int
    month: int
    year: int

class PaymentGatewayData(BaseModel):
    gateway: str
    count: int
    amount: float
    percentage: float

@router.get("/charts/user-growth", response_model=List[UserGrowthData])
async def get_user_growth_chart(
    current_admin: Annotated[AdminUser, Depends(get_current_admin_user)],
    days: int = Query(30, ge=7, le=365, description="Number of days to show")
):
    """Get user growth data for chart (last N days)."""
    db = get_database()
    
    now = datetime.utcnow()
    start_date = now - timedelta(days=days)
    
    # Get all users sorted by created_at
    users = list(db.users.find(
        {"created_at": {"$gte": start_date}},
        {"created_at": 1}
    ).sort("created_at", 1))
    
    # Generate daily data
    result = []
    current_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
    total_before_start = db.users.count_documents({"created_at": {"$lt": start_date}})
    
    for day in range(days + 1):
        date = current_date + timedelta(days=day)
        next_date = date + timedelta(days=1)
        
        # Count new users on this day
        new_users = db.users.count_documents({
            "created_at": {
                "$gte": date,
                "$lt": next_date
            }
        })
        
        # Total users up to this date
        total_users = total_before_start + db.users.count_documents({
            "created_at": {
                "$gte": start_date,
                "$lt": next_date
            }
        })
        
        result.append(UserGrowthData(
            date=date.strftime("%Y-%m-%d"),
            total_users=total_users,
            new_users=new_users
        ))
    
    return result

@router.get("/charts/revenue", response_model=List[RevenueChartData])
async def get_revenue_chart(
    current_admin: Annotated[AdminUser, Depends(get_current_admin_user)],
    days: int = Query(30, ge=7, le=365, description="Number of days to show")
):
    """Get revenue data for chart (last N days)."""
    db = get_database()
    
    now = datetime.utcnow()
    start_date = now - timedelta(days=days)
    
    result = []
    current_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
    
    for day in range(days + 1):
        date = current_date + timedelta(days=day)
        next_date = date + timedelta(days=1)
        
        # Aggregate revenue for this day
        pipeline = [
            {
                "$match": {
                    "status": "completed",
                    "completed_at": {
                        "$gte": date,
                        "$lt": next_date
                    }
                }
            },
            {
                "$group": {
                    "_id": None,
                    "total_revenue": {"$sum": "$amount"},
                    "count": {"$sum": 1}
                }
            }
        ]
        
        data = list(db.payments.aggregate(pipeline))
        
        result.append(RevenueChartData(
            date=date.strftime("%Y-%m-%d"),
            revenue=data[0]["total_revenue"] if data else 0,
            transactions=data[0]["count"] if data else 0
        ))
    
    return result

@router.get("/charts/subscription-trends", response_model=List[SubscriptionTrendData])
async def get_subscription_trends(
    current_admin: Annotated[AdminUser, Depends(get_current_admin_user)],
    days: int = Query(30, ge=7, le=365, description="Number of days to show")
):
    """Get subscription trends by plan type (last N days)."""
    db = get_database()
    
    now = datetime.utcnow()
    start_date = now - timedelta(days=days)
    
    result = []
    current_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
    
    for day in range(days + 1):
        date = current_date + timedelta(days=day)
        next_date = date + timedelta(days=1)
        
        # Count subscriptions by plan type created on this day
        pipeline = [
            {
                "$match": {
                    "created_at": {
                        "$gte": date,
                        "$lt": next_date
                    }
                }
            },
            {
                "$group": {
                    "_id": "$plan_type",
                    "count": {"$sum": 1}
                }
            }
        ]
        
        data = list(db.subscriptions.aggregate(pipeline))
        plan_counts = {item["_id"]: item["count"] for item in data}
        
        result.append(SubscriptionTrendData(
            date=date.strftime("%Y-%m-%d"),
            free=plan_counts.get("free", 0),
            week=plan_counts.get("week", 0),
            month=plan_counts.get("month", 0),
            year=plan_counts.get("year", 0)
        ))
    
    return result

@router.get("/charts/payment-gateways", response_model=List[PaymentGatewayData])
async def get_payment_gateway_distribution(
    current_admin: Annotated[AdminUser, Depends(get_current_admin_user)],
    days: Optional[int] = Query(None, ge=1, le=365, description="Filter by last N days (optional)")
):
    """Get payment distribution by gateway."""
    db = get_database()
    
    # Build match condition
    match_condition = {"status": "completed"}
    if days:
        start_date = datetime.utcnow() - timedelta(days=days)
        match_condition["completed_at"] = {"$gte": start_date}
    
    # Aggregate by gateway
    pipeline = [
        {"$match": match_condition},
        {
            "$group": {
                "_id": "$gateway",
                "count": {"$sum": 1},
                "total_amount": {"$sum": "$amount"}
            }
        }
    ]
    
    data = list(db.payments.aggregate(pipeline))
    
    # Calculate total for percentage
    total_count = sum(item["count"] for item in data)
    
    result = []
    for item in data:
        result.append(PaymentGatewayData(
            gateway=item["_id"],
            count=item["count"],
            amount=item["total_amount"],
            percentage=(item["count"] / total_count * 100) if total_count > 0 else 0
        ))
    
    # Sort by count descending
    result.sort(key=lambda x: x.count, reverse=True)
    
    return result

@router.get("/charts/user-activity")
async def get_user_activity_heatmap(
    current_admin: Annotated[AdminUser, Depends(get_current_admin_user)],
    days: int = Query(7, ge=1, le=30, description="Number of days to show")
):
    """Get user activity heatmap data (registrations by hour and day)."""
    db = get_database()
    
    now = datetime.utcnow()
    start_date = now - timedelta(days=days)
    
    # Get users created in the time range
    pipeline = [
        {
            "$match": {
                "created_at": {"$gte": start_date}
            }
        },
        {
            "$project": {
                "day_of_week": {"$dayOfWeek": "$created_at"},  # 1=Sunday, 7=Saturday
                "hour": {"$hour": "$created_at"}
            }
        },
        {
            "$group": {
                "_id": {
                    "day": "$day_of_week",
                    "hour": "$hour"
                },
                "count": {"$sum": 1}
            }
        }
    ]
    
    data = list(db.users.aggregate(pipeline))
    
    # Format as heatmap data
    heatmap = {}
    days_map = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
    
    for item in data:
        day_index = item["_id"]["day"] - 1  # Convert to 0-based (0=Sunday)
        hour = item["_id"]["hour"]
        day_name = days_map[day_index]
        
        if day_name not in heatmap:
            heatmap[day_name] = {}
        heatmap[day_name][hour] = item["count"]
    
    return {
        "days": days_map,
        "hours": list(range(24)),
        "data": heatmap
    }
