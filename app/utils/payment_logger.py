import logging
import os
from datetime import datetime
from logging.handlers import RotatingFileHandler

# Create logs directory if not exists
LOGS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'logs')
os.makedirs(LOGS_DIR, exist_ok=True)

# Payment receipt logger
def setup_payment_receipt_logger():
    """Setup dedicated logger for payment receipt tracking"""

    logger = logging.getLogger('payment_receipt')
    logger.setLevel(logging.INFO)

    # Avoid duplicate handlers
    if logger.handlers:
        return logger

    # File handler for payment receipts
    receipt_log_file = os.path.join(LOGS_DIR, 'payment_receipts.log')
    file_handler = RotatingFileHandler(
        receipt_log_file,
        maxBytes=10*1024*1024,  # 10MB
        backupCount=10
    )
    file_handler.setLevel(logging.INFO)

    # Format: timestamp | level | user_id | payment_id | transaction_id | status | message
    formatter = logging.Formatter(
        '%(asctime)s | %(levelname)s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(formatter)

    logger.addHandler(file_handler)

    # Also log to console in debug mode
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    return logger

# Initialize logger
payment_receipt_logger = setup_payment_receipt_logger()

def log_receipt_generation(payment_id: str, user_id: str, transaction_id: str, status: str, details: str = ""):
    """Log payment receipt generation event"""
    payment_receipt_logger.info(
        f"GENERATE | payment_id={payment_id} | user_id={user_id} | "
        f"transaction_id={transaction_id} | status={status} | {details}"
    )

def log_receipt_email_sent(payment_id: str, user_id: str, email: str, status: str, details: str = ""):
    """Log payment receipt email sent event"""
    payment_receipt_logger.info(
        f"EMAIL_SENT | payment_id={payment_id} | user_id={user_id} | "
        f"email={email} | status={status} | {details}"
    )

def log_receipt_error(payment_id: str, user_id: str, error_type: str, error_message: str):
    """Log payment receipt error"""
    payment_receipt_logger.error(
        f"ERROR | payment_id={payment_id} | user_id={user_id} | "
        f"error_type={error_type} | error={error_message}"
    )

def log_webhook_received(event_type: str, payment_id: str, status: str):
    """Log webhook event received"""
    payment_receipt_logger.info(
        f"WEBHOOK | event_type={event_type} | payment_id={payment_id} | status={status}"
    )

def log_subscription_created(payment_id: str, user_id: str, subscription_id: str, plan_type: str):
    """Log subscription creation"""
    payment_receipt_logger.info(
        f"SUBSCRIPTION | payment_id={payment_id} | user_id={user_id} | "
        f"subscription_id={subscription_id} | plan_type={plan_type}"
    )
