from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime
from enum import Enum

class PlanType(str, Enum):
    FREE = "free"
    WEEK = "week" 
    MONTH = "month"
    YEAR = "year"
    PAY_AS_YOU_GO = "pay_as_you_go"

class SubscriptionStatus(str, Enum):
    ACTIVE = "active"
    EXPIRED = "expired"
    CANCELLED = "cancelled"
    SUSPENDED = "suspended"

class PaymentStatus(str, Enum):
    PENDING = "pending"
    PAID = "paid"
    FAILED = "failed"
    REFUNDED = "refunded"

class Subscription(BaseModel):
    id: Optional[str] = Field(None, alias="_id")
    user_id: str = Field(..., description="User ID")
    plan_type: PlanType = Field(..., description="Subscription plan type")
    
    # Token limits and usage
    tokens_used: int = Field(default=0, description="Tokens used in current period")
    tokens_limit: int = Field(..., description="Token limit for this plan")
    
    # Request limits and usage  
    requests_used: int = Field(default=0, description="Requests used in current period")
    requests_limit: int = Field(..., description="Request limit for this plan")
    
    # Subscription details
    status: SubscriptionStatus = Field(default=SubscriptionStatus.ACTIVE)
    start_date: datetime = Field(default_factory=datetime.utcnow)
    end_date: datetime = Field(..., description="Subscription end date")
    
    # Billing
    price: float = Field(default=0.0, description="Price in VND")
    payment_status: PaymentStatus = Field(default=PaymentStatus.PENDING)
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Pay-as-you-go specific
    cost_per_1k_tokens: Optional[float] = Field(None, description="Cost per 1k tokens for PAYG")
    total_cost: Optional[float] = Field(default=0.0, description="Total cost for PAYG")
    
    class Config:
        populate_by_name = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
        protected_namespaces = ()
        protected_namespaces = ()
        
        json_schema_extra = {
            "example": {
                "user_id": "user123",
                "plan_type": "month",
                "tokens_limit": 500000,
                "requests_limit": 2000,
                "status": "active",
                "end_date": "2024-02-01T00:00:00Z",
                "price": 150000,
                "payment_status": "paid"
            }
        }

class UsageLog(BaseModel):
    id: Optional[str] = Field(None, alias="_id")
    user_id: str = Field(..., description="User ID")
    session_id: Optional[str] = Field(None, description="Chat session ID")
    
    # Token usage details
    tokens_consumed: int = Field(..., description="Total tokens consumed")
    input_tokens: int = Field(default=0, description="Input tokens")
    output_tokens: int = Field(default=0, description="Output tokens")
    
    # Request details
    request_type: str = Field(default="chat", description="Type of request")
    model_used: Optional[str] = Field(None, description="AI model used")
    endpoint: Optional[str] = Field(None, description="API endpoint called")
    
    # Cost calculation
    cost_vnd: Optional[float] = Field(default=0.0, description="Cost in VND")
    
    # Metadata
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    ip_address: Optional[str] = Field(None)
    user_agent: Optional[str] = Field(None)
    
    class Config:
        populate_by_name = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
        protected_namespaces = ()

class SubscriptionPlan(BaseModel):
    plan_type: PlanType
    name: str
    description: str
    tokens_limit: int
    requests_limit: int
    price: float
    duration_days: int
    features: list[str] = []
    
    class Config:
        json_schema_extra = {
            "example": {
                "plan_type": "month",
                "name": "Gói Tháng",
                "description": "Dành cho người dùng cá nhân",
                "tokens_limit": 500000,
                "requests_limit": 2000,
                "price": 150000,
                "duration_days": 30,
                "features": ["Unlimited task creation", "Priority support"]
            }
        }

# Predefined subscription plans
SUBSCRIPTION_PLANS: Dict[PlanType, SubscriptionPlan] = {
    PlanType.FREE: SubscriptionPlan(
        plan_type=PlanType.FREE,
        name="Gói Miễn Phí",
        description="Dùng thử miễn phí với giới hạn cơ bản",
        tokens_limit=100000,
        requests_limit=50,
        price=0,
        duration_days=30,
        features=["10k tokens/tháng", "50 requests/tháng", "Tính năng cơ bản"]
    ),
    PlanType.WEEK: SubscriptionPlan(
        plan_type=PlanType.WEEK,
        name="Gói Tuần",
        description="Hoàn hảo cho người dùng thử nghiệm",
        tokens_limit=1000000,
        requests_limit=500,
        price=50000,
        duration_days=7,
        features=["100k tokens/tuần", "500 requests/tuần", "Email support"]
    ),
    PlanType.MONTH: SubscriptionPlan(
        plan_type=PlanType.MONTH,
        name="Gói Tháng",
        description="Phổ biến nhất cho cá nhân và team nhỏ",
        tokens_limit=5000000,
        requests_limit=2000,
        price=150000,
        duration_days=30,
        features=["500k tokens/tháng", "2000 requests/tháng", "Priority support", "Advanced features"]
    ),
    PlanType.YEAR: SubscriptionPlan(
        plan_type=PlanType.YEAR,
        name="Gói Năm",
        description="Tiết kiệm nhất cho power users",
        tokens_limit=60000000,
        requests_limit=25000,
        price=1500000,
        duration_days=365,
        features=["6M tokens/năm", "25k requests/năm", "24/7 support", "Custom integrations", "Analytics dashboard"]
    ),
    PlanType.PAY_AS_YOU_GO: SubscriptionPlan(
        plan_type=PlanType.PAY_AS_YOU_GO,
        name="Trả Theo Sử Dụng",
        description="Linh hoạt nhất, chỉ trả cho những gì sử dụng",
        tokens_limit=999999999,
        requests_limit=999999,
        price=0,  # Base price, actual cost calculated per usage
        duration_days=365,
        features=["Unlimited tokens", "Unlimited requests", "Pay per use", "1000 VND/1k tokens"]
    )
}