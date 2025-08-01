from datetime import timedelta
from typing import Any, Tuple

import jwt
from django.conf import settings
from django.utils import timezone
from passlib.context import CryptContext

from core.exceptions import Unauthorized


class Security:
    _pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

    @staticmethod
    def get_password_hash(password: str) -> str:
        return str(Security._pwd_context.hash(password))

    @staticmethod
    def verify_password(password: str, hashed_password: str) -> bool:
        return bool(Security._pwd_context.verify(password, hashed_password))

    @staticmethod
    def create_token(data: dict):
        """Create JWT token with expiration"""
        payload = {
            "staff_id": data["staff_id"],
            "role": data["role"],
            "exp": timezone.now() + timedelta(minutes=settings.TOKEN_EXPIRE_MINUTES),
            "iat": timezone.now(),
        }
        return jwt.encode(payload, settings.TOKEN_SECRET, algorithm=settings.ALGORITHM)

    @staticmethod
    def verify_token(token: str) -> Tuple[str, Any]:
        """Verify JWT token and return staff_id and expiry"""
        try:
            payload = jwt.decode(token, settings.TOKEN_SECRET, algorithms=[settings.ALGORITHM])

            staff_id = payload.get("staff_id")
            if not staff_id:
                raise Unauthorized("Invalid token: missing staff_id")

            # JWT library handles expiration automatically
            # If token is expired, jwt.decode will raise jwt.ExpiredSignatureError

            return staff_id, payload.get("exp")
        except jwt.ExpiredSignatureError:
            raise Unauthorized("Token expired")
        except jwt.InvalidTokenError as e:
            raise Unauthorized(f"Invalid token: {str(e)}")
        except Exception as e:
            raise Unauthorized(f"Error verifying token: {str(e)}")
