import traceback
from typing import Optional, Dict, Any
from app.models.payment import Payment, PaymentGateway as PaymentGatewayEnum, PaymentStatus, CheckoutSession
from app.models.subscription import PlanType, SUBSCRIPTION_PLANS, SubscriptionStatus, PaymentStatus as SubPaymentStatus
from app.services.payment import StripeGateway
from app.core.config import settings
from app.utils.payment_logger import (
    log_receipt_generation,
    log_receipt_email_sent,
    log_receipt_error,
    log_webhook_received,
    log_subscription_created
)
from app.services.email_service import EmailService
from app.services.pdf_service import PDFReceiptService

from datetime import datetime, timedelta, timezone
from bson import ObjectId
import logging
import asyncio

logger = logging.getLogger(__name__)

class PaymentService:
    """Main payment service using factory pattern"""

    def __init__(self, db):
        self.db = db
        self.payments_collection = db["payments"]
        self.subscriptions_collection = db["subscriptions"]

        # Initialize gateways
        self.stripe = StripeGateway(
            secret_key=settings.STRIPE_SECRET_KEY,
            publishable_key=settings.STRIPE_PUBLISHABLE_KEY,
            webhook_secret=settings.STRIPE_WEBHOOK_SECRET
        )


    def _get_gateway(self, gateway: PaymentGatewayEnum):
        """Get gateway instance"""
        if gateway == PaymentGatewayEnum.STRIPE:
            return self.stripe
        # Add more gateways here
        raise ValueError(f"Unsupported gateway: {gateway}")

    def create_checkout_session(
        self,
        user_id: str,
        plan_type: str,
        gateway: PaymentGatewayEnum,
        success_url: str,
        cancel_url: str
    ) -> CheckoutSession:
        """Create checkout session for payment"""

        # Get plan details
        try:
            plan = SUBSCRIPTION_PLANS[PlanType(plan_type)]
        except (KeyError, ValueError):
            raise ValueError(f"Invalid plan type: {plan_type}")

        # Create payment record
        payment = Payment(
            user_id=user_id,
            plan_type=plan_type,
            amount=plan.price,
            currency="VND",
            gateway=gateway,
            status=PaymentStatus.PENDING
        )

        # Insert to DB
        result = self.payments_collection.insert_one(payment.model_dump(by_alias=True, exclude={'id'}))
        payment_id = str(result.inserted_id)

        # Create checkout session with gateway
        gateway_client = self._get_gateway(gateway)

        try:
            session_data = gateway_client.create_checkout_session(
                amount=plan.price,
                currency="VND",
                user_id=user_id,
                plan_type=plan_type,
                success_url=success_url,
                cancel_url=cancel_url,
                metadata={
                    'payment_id': payment_id,
                    'plan_name': plan.name
                }
            )

            # Update payment with session info
            self.payments_collection.update_one(
                {'_id': result.inserted_id},
                {
                    '$set': {
                        'checkout_session_id': session_data['session_id'],
                        'transaction_id': session_data['payment_id'],
                        'updated_at': datetime.now(timezone.utc)
                    }
                }
            )

            return CheckoutSession(
                session_id=session_data['session_id'],
                checkout_url=session_data['checkout_url'],
                payment_id=payment_id
            )

        except Exception as e:
            # Mark payment as failed
            self.payments_collection.update_one(
                {'_id': result.inserted_id},
                {
                    '$set': {
                        'status': PaymentStatus.FAILED,
                        'error_message': str(e),
                        'updated_at': datetime.now(timezone.utc)
                    }
                }
            )
            raise

    async def verify_payment(self, payment_id: str, gateway: PaymentGatewayEnum) -> Payment:
        """Verify payment status with gateway"""

        payment = await self.payments_collection.find_one({'_id': payment_id})
        if not payment:
            raise ValueError(f"Payment not found: {payment_id}")

        gateway_client = self._get_gateway(gateway)

        try:
            status = await gateway_client.get_payment_status(payment['transaction_id'])

            # Update payment status
            await self.payments_collection.update_one(
                {'_id': payment_id},
                {
                    '$set': {
                        'status': status,
                        'updated_at': datetime.now(timezone.utc),
                        'completed_at': datetime.now(timezone.utc) if status == 'completed' else None
                    }
                }
            )

            payment['status'] = status
            return Payment(**payment)

        except Exception as e:
            logger.error(f"Error verifying payment: {str(e)}")
            raise

    def handle_webhook(
        self,
        gateway: PaymentGatewayEnum,
        payload: bytes,
        signature: str
    ) -> Dict[str, Any]:
        """Handle webhook from payment gateway"""

        logger.info(f"Received webhook from {gateway}")

        gateway_client = self._get_gateway(gateway)

        # Verify webhook
        logger.info("Verifying webhook signature...")
        event = gateway_client.verify_webhook(payload, signature)
        logger.info(f"Webhook verified: {event.get('type')}")

        if gateway == PaymentGatewayEnum.STRIPE:
            return self._handle_stripe_webhook(event)

        return {'status': 'unhandled'}

    def _handle_stripe_webhook(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Handle Stripe webhook events"""

        event_type = event['type']
        logger.info(f"Processing Stripe webhook: {event_type}")

        if event_type == 'checkout.session.completed':
            session = event['data']['object']
            payment_id = session['metadata'].get('payment_id')

            if payment_id:
                transaction_id = session.get('payment_intent', 'N/A')

                # Log webhook received
                log_webhook_received(event_type, payment_id, 'processing')

                self.payments_collection.update_one(
                    {'_id': ObjectId(payment_id)},
                    {
                        '$set': {
                            'status': PaymentStatus.COMPLETED,
                            'transaction_id': transaction_id,
                            'completed_at': datetime.now(timezone.utc),
                            'updated_at': datetime.now(timezone.utc)
                        }
                    }
                )

                # Activate subscription
                payment = self.payments_collection.find_one({'_id': ObjectId(payment_id)})
                if payment:
                    self._create_subscription_from_payment(payment)
                    # Send receipt email
                    self._send_payment_receipt_email(payment)

                # Log success
                log_webhook_received(event_type, payment_id, 'completed')

                return {'status': 'success', 'payment_id': payment_id}

        elif event_type == 'payment_intent.succeeded':
            # Handle payment intent success
            logger.info(f"Payment intent succeeded: {event['data']['object'].get('id')}")

        elif event_type == 'payment_intent.payment_failed':
            # Handle payment failure
            logger.info(f"Payment intent failed: {event['data']['object'].get('id')}")

        return {'status': 'processed', 'event_type': event_type}

    def get_payment(self, payment_id: str) -> Optional[Payment]:
        """Get payment by ID"""
        payment = self.payments_collection.find_one({'_id': payment_id})
        return Payment(**payment) if payment else None

    def get_user_payments(self, user_id: str, limit: int = 10) -> list[Payment]:
        """Get user's payment history"""
        cursor = self.payments_collection.find({'user_id': user_id}).sort('created_at', -1).limit(limit)
        payments = list(cursor)
        return [Payment(**p) for p in payments]

    def _create_subscription_from_payment(self, payment: dict):
        """Create or update subscription after successful payment"""
        try:
            user_id = payment['user_id']
            plan_type = payment['plan_type']

            # Get plan details
            plan = SUBSCRIPTION_PLANS[PlanType(plan_type)]

            # Calculate end date
            start_date = datetime.now(timezone.utc)
            end_date = start_date + timedelta(days=plan.duration_days)

            # Check if user already has subscription
            existing_sub = self.subscriptions_collection.find_one({'user_id': user_id})

            subscription_data = {
                'user_id': user_id,
                'plan_type': plan_type,
                'tokens_used': 0,
                'tokens_limit': plan.tokens_limit,
                'requests_used': 0,
                'requests_limit': plan.requests_limit,
                'status': SubscriptionStatus.ACTIVE.value,
                'start_date': start_date,
                'end_date': end_date,
                'price': plan.price,
                'payment_status': SubPaymentStatus.PAID.value,
                'updated_at': start_date
            }

            if plan_type == PlanType.PAY_AS_YOU_GO.value:
                subscription_data['cost_per_1k_tokens'] = 1000.0
                subscription_data['total_cost'] = 0.0

            if existing_sub:
                # Update existing subscription
                self.subscriptions_collection.update_one(
                    {'user_id': user_id},
                    {'$set': subscription_data}
                )
                logger.info(f"Updated subscription for user {user_id} to {plan_type}")
                log_subscription_created(
                    str(payment['_id']),
                    user_id,
                    str(existing_sub['_id']),
                    plan_type
                )
            else:
                # Create new subscription
                subscription_data['created_at'] = start_date
                result = self.subscriptions_collection.insert_one(subscription_data)
                logger.info(f"Created subscription {result.inserted_id} for user {user_id}")

                # Link subscription to payment
                self.payments_collection.update_one(
                    {'_id': payment['_id']},
                    {'$set': {'subscription_id': str(result.inserted_id)}}
                )

                # Log subscription creation
                log_subscription_created(
                    str(payment['_id']),
                    user_id,
                    str(result.inserted_id),
                    plan_type
                )

        except Exception as e:
            logger.error(f"Error creating subscription from payment: {str(e)}")
            traceback.print_exc()

    def _send_payment_receipt_email(self, payment: dict):
        """Send payment receipt email with PDF attachment to user"""
        try:
            user_id = payment['user_id']

            # Get user email from database
            user = self.db['users'].find_one({'_id': ObjectId(user_id)})
            if not user or not user.get('email'):
                logger.warning(f"User {user_id} not found or no email")
                return

            user_email = user['email']
            plan = SUBSCRIPTION_PLANS[PlanType(payment['plan_type'])]

            # Generate PDF receipt
            pdf_service = PDFReceiptService()

            pdf_buffer = pdf_service.generate_receipt(
                payment_data=payment,
                user_data=user,
                plan_data=plan.model_dump()
            )
            logger.info("PDF receipt generated successfully")

            # Log PDF generation
            log_receipt_generation(
                str(payment.get('_id')),
                user_id,
                payment.get('transaction_id', 'N/A'),
                'success',
                f"PDF size: {len(pdf_buffer.getvalue())} bytes"
            )

            # Create email content
            subject = "Xác nhận thanh toán - Biên lai đăng ký"

            html_content = f"""
            <html>
            <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
                <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; border-radius: 10px 10px 0 0;">
                    <h1 style="margin: 0;">✅ Thanh toán thành công!</h1>
                </div>

                <div style="background: #f9fafb; padding: 30px; border-radius: 0 0 10px 10px;">
                    <p style="font-size: 16px; color: #333;">Xin chào <strong>{user.get('username', 'bạn')}</strong>,</p>

                    <p style="font-size: 16px; color: #333;">Cảm ơn bạn đã đăng ký! Thanh toán của bạn đã được xử lý thành công.</p>

                    <div style="background: white; padding: 20px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #667eea;">
                        <h2 style="margin-top: 0; color: #667eea;">📋 Chi tiết biên lai</h2>

                        <table style="width: 100%; border-collapse: collapse;">
                            <tr>
                                <td style="padding: 10px 0; border-bottom: 1px solid #e5e7eb;"><strong>Mã giao dịch:</strong></td>
                                <td style="padding: 10px 0; border-bottom: 1px solid #e5e7eb; text-align: right;">{payment.get('transaction_id', 'N/A')}</td>
                            </tr>
                            <tr>
                                <td style="padding: 10px 0; border-bottom: 1px solid #e5e7eb;"><strong>Gói đăng ký:</strong></td>
                                <td style="padding: 10px 0; border-bottom: 1px solid #e5e7eb; text-align: right;">{plan.name}</td>
                            </tr>
                            <tr>
                                <td style="padding: 10px 0; border-bottom: 1px solid #e5e7eb;"><strong>Số tiền:</strong></td>
                                <td style="padding: 10px 0; border-bottom: 1px solid #e5e7eb; text-align: right;">{payment['amount']:,.0f} {payment['currency']}</td>
                            </tr>
                            <tr>
                                <td style="padding: 10px 0; border-bottom: 1px solid #e5e7eb;"><strong>Ngày thanh toán:</strong></td>
                                <td style="padding: 10px 0; border-bottom: 1px solid #e5e7eb; text-align: right;">{payment.get('completed_at', datetime.now(timezone.utc)).strftime('%d/%m/%Y %H:%M')}</td>
                            </tr>
                            <tr>
                                <td style="padding: 10px 0;"><strong>Trạng thái:</strong></td>
                                <td style="padding: 10px 0; text-align: right;"><span style="background: #10b981; color: white; padding: 4px 12px; border-radius: 20px; font-size: 12px;">Đã thanh toán</span></td>
                            </tr>
                        </table>
                    </div>

                    <div style="background: #eff6ff; padding: 15px; border-radius: 8px; border-left: 4px solid #3b82f6;">
                        <p style="margin: 0; color: #1e40af;"><strong>🎉 Gói của bạn đã được kích hoạt!</strong></p>
                        <p style="margin: 10px 0 0 0; color: #1e40af;">Bắt đầu sử dụng ngay với {plan.tokens_limit:,} tokens và {plan.requests_limit:,} requests.</p>
                    </div>

                    <p style="margin-top: 30px; color: #6b7280; font-size: 14px;">
                        Nếu bạn có bất kỳ câu hỏi nào, vui lòng liên hệ với chúng tôi tại {settings.SMTP_FROM_EMAIL}
                    </p>

                    <p style="color: #6b7280; font-size: 14px;">
                        Trân trọng,<br>
                        <strong>Đội ngũ Task Management</strong>
                    </p>
                </div>

                <div style="text-align: center; padding: 20px; color: #9ca3af; font-size: 12px;">
                    <p>Email này được gửi tự động, vui lòng không trả lời.</p>
                </div>
            </body>
            </html>
            """

            # Send email async
           
            email_service = EmailService()

            # Prepare PDF attachment
            pdf_filename = f"receipt_{payment.get('transaction_id', payment.get('_id'))}.pdf"
            attachments = [
                {
                    'filename': pdf_filename,
                    'content': pdf_buffer
                }
            ]

            # Run async email in background thread to avoid event loop conflict
            import threading

            def send_email_sync():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    loop.run_until_complete(email_service.send_email(
                        to_emails=[user_email],
                        subject=subject,
                        html_content=html_content,
                        attachments=attachments
                    ))
                finally:
                    loop.close()

            # Run in separate thread to avoid blocking
            email_thread = threading.Thread(target=send_email_sync)
            email_thread.start()
            email_thread.join(timeout=30)  # Wait max 30 seconds

            logger.info(f"Sent payment receipt email with PDF to {user_email}")

            # Log email sent
            log_receipt_email_sent(
                str(payment.get('_id')),
                user_id,
                user_email,
                'success',
                f"attachment={pdf_filename}"
            )

        except Exception as e:
            logger.error(f"Error sending payment receipt email: {str(e)}")

            # Log error
            log_receipt_error(
                str(payment.get('_id', 'unknown')),
                user_id,
                'email_send_failed',
                str(e)
            )

            traceback.print_exc()
