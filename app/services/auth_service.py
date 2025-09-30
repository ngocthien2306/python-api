from datetime import datetime, timedelta
from typing import Optional
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from app.core.config import settings
from app.models.user import User
from app.repositories.user import UserRepository
from app.services.email_service import EmailService
import logging

logger = logging.getLogger(__name__)

class AuthService:
    def __init__(self, user_repository: UserRepository):
        self.user_repository = user_repository
        self.email_service = EmailService()
        self.serializer = URLSafeTimedSerializer(settings.SECRET_KEY)
    
    def generate_verification_token(self, email: str) -> str:
        """Generate email verification token."""
        return self.serializer.dumps(email, salt="email-verification")
    
    def generate_password_reset_token(self, email: str) -> str:
        """Generate password reset token."""
        return self.serializer.dumps(email, salt="password-reset")
    
    def verify_email_token(self, token: str, max_age: int = None) -> Optional[str]:
        """Verify email token and return email if valid."""
        try:
            if max_age is None:
                max_age = settings.EMAIL_VERIFICATION_EXPIRE_HOURS * 3600  # Convert hours to seconds
            
            email = self.serializer.loads(
                token,
                salt="email-verification",
                max_age=max_age
            )
            return email
        except (BadSignature, SignatureExpired) as e:
            logger.warning(f"Invalid or expired email verification token: {str(e)}")
            return None
    
    def verify_password_reset_token(self, token: str) -> Optional[str]:
        """Verify password reset token and return email if valid."""
        try:
            email = self.serializer.loads(
                token,
                salt="password-reset",
                max_age=3600  # 1 hour
            )
            return email
        except (BadSignature, SignatureExpired) as e:
            logger.warning(f"Invalid or expired password reset token: {str(e)}")
            return None
    
    async def send_verification_email(self, user: User) -> bool:
        """Send verification email to user."""
        try:
            verification_token = self.generate_verification_token(user.email)
            success = await self.email_service.send_verification_email(
                email=user.email,
                username=user.username,
                verification_token=verification_token
            )
            
            if success:
                logger.info(f"Verification email sent to {user.email}")
            else:
                logger.error(f"Failed to send verification email to {user.email}")
            
            return success
        except Exception as e:
            logger.error(f"Error sending verification email to {user.email}: {str(e)}")
            return False
    
    async def send_password_reset_email(self, email: str) -> bool:
        """Send password reset email."""
        try:
            user = self.user_repository.get_user_by_email(email)
            if not user:
                # Don't reveal if email exists or not for security
                logger.warning(f"Password reset requested for non-existent email: {email}")
                return True  # Return True to not reveal email existence
            
            reset_token = self.generate_password_reset_token(email)
            success = await self.email_service.send_password_reset_email(
                email=email,
                username=user.username,
                reset_token=reset_token
            )
            
            if success:
                logger.info(f"Password reset email sent to {email}")
            else:
                logger.error(f"Failed to send password reset email to {email}")
            
            return success
        except Exception as e:
            logger.error(f"Error sending password reset email to {email}: {str(e)}")
            return False
    
    def verify_user_email(self, token: str) -> bool:
        """Verify user email using token."""
        try:
            email = self.verify_email_token(token)
            if not email:
                return False
            
            user = self.user_repository.get_user_by_email(email)
            if not user:
                logger.warning(f"Email verification attempted for non-existent user: {email}")
                return False
            
            if user.is_verified:
                logger.info(f"User {email} already verified")
                return True
            
            # Update user verification status
            success = self.user_repository.verify_user_email(user.id)
            if success:
                logger.info(f"Successfully verified email for user: {email}")
            else:
                logger.error(f"Failed to update verification status for user: {email}")
            
            return success
        except Exception as e:
            logger.error(f"Error verifying user email: {str(e)}")
            return False
    
    def reset_user_password(self, token: str, new_password: str) -> bool:
        """Reset user password using token."""
        try:
            email = self.verify_password_reset_token(token)
            if not email:
                return False
            
            user = self.user_repository.get_user_by_email(email)
            if not user:
                logger.warning(f"Password reset attempted for non-existent user: {email}")
                return False
            
            # Update user password
            success = self.user_repository.update_user_password(user.id, new_password)
            if success:
                logger.info(f"Successfully reset password for user: {email}")
            else:
                logger.error(f"Failed to reset password for user: {email}")
            
            return success
        except Exception as e:
            logger.error(f"Error resetting user password: {str(e)}")
            return False