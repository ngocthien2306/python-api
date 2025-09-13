"""
Web Push API Service - No Firebase dependency
Implements RFC 8030 Web Push Protocol
"""

import json
import base64
import hashlib
import hmac
import time
import traceback
from typing import Dict, Optional, Tuple
from datetime import datetime, timedelta
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric.utils import encode_dss_signature
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.backends import default_backend
import requests
from urllib.parse import urlparse


class VAPIDKeys:
    """VAPID (Voluntary Application Server Identification) Key Management"""
    
    @staticmethod
    def generate_keys() -> Tuple[str, str]:
        """Generate new VAPID key pair"""
        private_key = ec.generate_private_key(ec.SECP256R1(), default_backend())
        
        # Private key (DER format, base64url encoded)
        private_bytes = private_key.private_bytes(
            encoding=serialization.Encoding.DER,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )
        private_key_b64 = base64.urlsafe_b64encode(private_bytes).decode('utf-8').rstrip('=')
        
        # Public key (uncompressed point format, base64url encoded)
        public_key = private_key.public_key()
        public_bytes = public_key.public_bytes(
            encoding=serialization.Encoding.X962,
            format=serialization.PublicFormat.UncompressedPoint
        )
        public_key_b64 = base64.urlsafe_b64encode(public_bytes).decode('utf-8').rstrip('=')
        
        return private_key_b64, public_key_b64
    
    @staticmethod
    def get_vapid_headers(private_key: str, public_key: str, 
                         endpoint: str, subject: str = "mailto:admin@example.com") -> Dict[str, str]:
        """Generate VAPID headers for authentication"""
        print(f"🔐 Generating VAPID headers for endpoint: {endpoint}")
        print(f"🔑 Using public key: {public_key[:20]}...")
        
        # JWT Header
        header = {
            "typ": "JWT",
            "alg": "ES256"
        }
        
        # JWT Payload
        aud = urlparse(endpoint).scheme + "://" + urlparse(endpoint).netloc
        payload = {
            "aud": aud,
            "exp": int(time.time()) + 3600,  # 1 hour expiry
            "sub": subject
        }
        
        # Encode header and payload
        header_b64 = base64.urlsafe_b64encode(
            json.dumps(header, separators=(',', ':')).encode('utf-8')
        ).decode('utf-8').rstrip('=')
        
        payload_b64 = base64.urlsafe_b64encode(
            json.dumps(payload, separators=(',', ':')).encode('utf-8')
        ).decode('utf-8').rstrip('=')
        
        # Create signature
        signing_input = f"{header_b64}.{payload_b64}".encode('utf-8')
        
        # Decode private key (DER format)
        private_key_bytes = base64.urlsafe_b64decode(private_key + '==')
        private_key_obj = serialization.load_der_private_key(
            private_key_bytes, 
            password=None, 
            backend=default_backend()
        )
        
        # Sign
        signature = private_key_obj.sign(signing_input, ec.ECDSA(hashes.SHA256()))
        
        # Convert DER signature to r,s values  
        from cryptography.hazmat.primitives.asymmetric.utils import decode_dss_signature
        r, s = decode_dss_signature(signature)
        
        # Convert to 32-byte format for JWT
        raw_signature = r.to_bytes(32, 'big') + s.to_bytes(32, 'big')
        signature_b64 = base64.urlsafe_b64encode(raw_signature).decode('utf-8').rstrip('=')
        
        # Create JWT
        jwt_token = f"{header_b64}.{payload_b64}.{signature_b64}"
        
        return {
            "Authorization": f"vapid t={jwt_token}, k={public_key}",
            "Crypto-Key": f"p256ecdsa={public_key}"
        }


class WebPushEncryption:
    """Handle Web Push message encryption (RFC 8291)"""
    
    @staticmethod
    def encrypt_message(message: str, p256dh: str, auth: str) -> Tuple[bytes, Dict[str, str]]:
        """Encrypt message for Web Push"""
        import os
        from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
        from cryptography.hazmat.primitives.kdf.hkdf import HKDF
        
        # Decode keys
        receiver_public_key = base64.urlsafe_b64decode(p256dh + '==')
        auth_secret = base64.urlsafe_b64decode(auth + '==')
        
        # Generate ephemeral key pair
        ephemeral_private_key = ec.generate_private_key(ec.SECP256R1(), default_backend())
        ephemeral_public_key = ephemeral_private_key.public_key()
        
        # Get ephemeral public key bytes
        ephemeral_public_bytes = ephemeral_public_key.public_bytes(
            encoding=serialization.Encoding.X962,
            format=serialization.PublicFormat.UncompressedPoint
        )
        
        # Shared secret calculation
        receiver_key_obj = ec.EllipticCurvePublicKey.from_encoded_point(
            ec.SECP256R1(), receiver_public_key
        )
        shared_secret = ephemeral_private_key.exchange(ec.ECDH(), receiver_key_obj)
        
        # Key derivation
        def hkdf_extract_expand(salt: bytes, ikm: bytes, info: bytes, length: int) -> bytes:
            hkdf = HKDF(
                algorithm=hashes.SHA256(),
                length=length,
                salt=salt,
                info=info,
                backend=default_backend()
            )
            return hkdf.derive(ikm)
        
        # Auth info
        auth_info = b"WebPush: info\x00" + receiver_public_key + ephemeral_public_bytes
        prk = hkdf_extract_expand(auth_secret, shared_secret, b"", 32)
        
        # Content encryption key and nonce
        content_encryption_key_info = b"Content-Encoding: aes128gcm\x00"
        content_encryption_key = hkdf_extract_expand(
            auth_secret, prk, content_encryption_key_info, 16
        )
        
        nonce_info = b"Content-Encoding: nonce\x00"
        nonce = hkdf_extract_expand(auth_secret, prk, nonce_info, 12)
        
        # Prepare message
        message_bytes = message.encode('utf-8')
        
        # Add padding and delimiter
        padded_message = message_bytes + b'\x02'
        
        # Encrypt
        cipher = Cipher(algorithms.AES(content_encryption_key), modes.GCM(nonce), backend=default_backend())
        encryptor = cipher.encryptor()
        ciphertext = encryptor.update(padded_message) + encryptor.finalize()
        
        # Combine ciphertext and tag
        encrypted_data = ciphertext + encryptor.tag
        
        # Headers
        headers = {
            "Crypto-Key": f"dh={base64.urlsafe_b64encode(ephemeral_public_bytes).decode('utf-8').rstrip('=')}",
            "Encryption": f"salt={base64.urlsafe_b64encode(os.urandom(16)).decode('utf-8').rstrip('=')}",
            "Content-Encoding": "aes128gcm"
        }
        
        return encrypted_data, headers


class WebPushService:
    """Main Web Push Service"""
    
    def __init__(self, private_key: str, public_key: str, subject: str = "mailto:admin@example.com"):
        self.private_key = private_key
        self.public_key = public_key
        self.subject = subject
    
    async def send_notification(self, subscription: Dict, payload: Dict) -> bool:
        """Send push notification to a subscription"""
        try:
            endpoint = subscription.get('endpoint')
            p256dh = subscription.get('keys', {}).get('p256dh')
            auth = subscription.get('keys', {}).get('auth')
            
            if not all([endpoint, p256dh, auth]):
                raise ValueError("Invalid subscription format")
            
            # Prepare message
            message = json.dumps(payload)
            
            # Encrypt message
            encrypted_data, crypto_headers = WebPushEncryption.encrypt_message(
                message, p256dh, auth
            )
            
            # Get VAPID headers
            vapid_headers = VAPIDKeys.get_vapid_headers(
                self.private_key, self.public_key, endpoint, self.subject
            )
            
            # Combine headers
            headers = {
                "Content-Type": "application/octet-stream",
                "Content-Length": str(len(encrypted_data)),
                "TTL": "2419200",  # 4 weeks
                **vapid_headers,
                **crypto_headers
            }
            
            # Send request
            response = requests.post(
                endpoint,
                data=encrypted_data,
                headers=headers,
                timeout=30
            )
            
            # Handle response
            if response.status_code == 200 or response.status_code == 201:
                return True
            elif response.status_code == 410:
                # Subscription expired - should remove from database
                print(f"Push subscription expired: {endpoint}")
                return False
            else:
                print(f"Push notification failed: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            traceback.print_exc()
            print(f"Error sending push notification: {e}")
            return False
    
    async def send_to_multiple(self, subscriptions: list, payload: Dict) -> Dict[str, int]:
        """Send notification to multiple subscriptions"""
        results = {"success": 0, "failed": 0, "expired": 0}
        
        for subscription in subscriptions:
            try:
                success = await self.send_notification(subscription, payload)
                if success:
                    results["success"] += 1
                else:
                    results["failed"] += 1
            except Exception as e:
                print(f"Failed to send to subscription: {e}")
                results["failed"] += 1
        
        return results


class WebPushManager:
    """High-level Web Push Manager"""
    
    def __init__(self):
        from app.core.config import settings
        
        # Generate VAPID keys if not provided in settings
        if not settings.VAPID_PRIVATE_KEY or not settings.VAPID_PUBLIC_KEY:
            private_key, public_key = VAPIDKeys.generate_keys()
            self.private_key = private_key
            self.public_key = public_key
            print("Generated new VAPID keys. Add to your .env.local file:")
            print(f"VAPID_PRIVATE_KEY={self.private_key}")
            print(f"VAPID_PUBLIC_KEY={self.public_key}")
        else:
            self.private_key = settings.VAPID_PRIVATE_KEY
            self.public_key = settings.VAPID_PUBLIC_KEY
        
        self.subject = settings.VAPID_SUBJECT
        
        self.push_service = WebPushService(
            self.private_key, 
            self.public_key, 
            self.subject
        )
    
    def get_public_key(self) -> str:
        """Get public key for frontend"""
        return self.public_key
    
    async def subscribe_user(self, user_id: str, subscription: Dict) -> bool:
        """Subscribe user to push notifications"""
        try:
            from app.core.dependencies import get_user_repository
            user_repo = get_user_repository()
            
            # Validate subscription format
            required_fields = ['endpoint', 'keys']
            if not all(field in subscription for field in required_fields):
                return False
            
            if not all(key in subscription['keys'] for key in ['p256dh', 'auth']):
                return False
            
            # Save subscription to user profile using repository
            success = user_repo.add_push_subscription(user_id, subscription)
            return success
            
        except Exception as e:
            print(f"Error subscribing user: {e}")
            return False
    
    async def unsubscribe_user(self, user_id: str, endpoint: str) -> bool:
        """Unsubscribe user from push notifications"""
        try:
            from app.core.dependencies import get_user_repository
            user_repo = get_user_repository()
            
            # Remove subscription from user profile using repository
            success = user_repo.remove_push_subscription(user_id, endpoint)
            return success
            
        except Exception as e:
            print(f"Error unsubscribing user: {e}")
            return False
    
    async def send_to_user(self, user_id: str, payload: Dict) -> bool:
        """Send notification to all user's subscriptions"""
        try:
            print(f"🔔 Sending push notification to user {user_id}")
            print(f"📦 Payload: {payload}")
            print(f"🔑 Using VAPID keys - Private: {self.private_key[:20]}... Public: {self.public_key[:20]}...")
            
            from app.core.dependencies import get_user_repository
            user_repo = get_user_repository()
            
            # Get user's subscriptions
            user = user_repo.get_user_by_id(user_id)
            if not user:
                print(f"❌ User {user_id} not found")
                return False
            
            subscriptions = getattr(user, 'push_subscriptions', [])
            if not subscriptions:
                print(f"❌ No push subscriptions found for user {user_id}")
                return False
            
            print(f"📱 Found {len(subscriptions)} subscription(s)")
            
            # Send to all subscriptions
            results = await self.push_service.send_to_multiple(subscriptions, payload)
            
            # Clean up expired subscriptions
            if results["expired"] > 0:
                await self._cleanup_expired_subscriptions(user_id, subscriptions)
            
            return results["success"] > 0
            
        except Exception as e:
            traceback.print_exc()
            print(f"Error sending to user: {e}")
            return False
    
    async def _cleanup_expired_subscriptions(self, user_id: str, subscriptions: list):
        """Remove expired subscriptions from user profile"""
        # This would be implemented based on which subscriptions failed with 410
        pass


# Singleton instance
web_push_manager = WebPushManager()