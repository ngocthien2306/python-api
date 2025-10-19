from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from enum import Enum

class PaymentGateway(str, Enum):
    STRIPE = "stripe"
    PAYPAL = "paypal"
    VNPAY = "vnpay"
    MOMO = "momo"

class PaymentStatus(str, Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"
    CANCELLED = "cancelled"

class Payment(BaseModel):
    id: Optional[str] = Field(None, alias="_id")
    user_id: str
    subscription_id: Optional[str] = None
    plan_type: str

    # Payment details
    amount: float
    currency: str = "VND"
    gateway: PaymentGateway

    # Gateway specific
    transaction_id: Optional[str] = None  # ID from gateway
    payment_intent_id: Optional[str] = None  # For Stripe
    checkout_session_id: Optional[str] = None  # For Stripe Checkout

    # Status
    status: PaymentStatus = PaymentStatus.PENDING

    # Metadata
    metadata: Optional[dict] = {}
    error_message: Optional[str] = None

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None

    class Config:
        populate_by_name = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class PaymentIntent(BaseModel):
    payment_id: str
    client_secret: str
    publishable_key: str
    amount: float
    currency: str

class CheckoutSession(BaseModel):
    session_id: str
    checkout_url: str
    payment_id: str
