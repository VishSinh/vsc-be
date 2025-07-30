from datetime import timedelta
from typing import Any, Tuple

from django.conf import settings
from django.utils import timezone
from jose import jwt
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
    def create_token(data: dict) -> str:
        data["exp"] = timezone.now() + timedelta(minutes=settings.TOKEN_EXPIRE_MINUTES)
        return str(jwt.encode(data, settings.TOKEN_SECRET, algorithm=settings.ALGORITHM))

    @staticmethod
    def verify_token(token: str) -> Tuple[str, Any]:
        try:
            decoded_token = jwt.decode(token, settings.TOKEN_SECRET, algorithms=[settings.ALGORITHM])
            staff_id = decoded_token.get("staff_id")
            expiry = timezone.datetime.fromtimestamp(decoded_token.get("exp"), tz=timezone.utc)

            if expiry < timezone.now():
                raise Unauthorized("Token expired")

            return staff_id, expiry
        except Exception as e:
            raise Unauthorized("Error verifying token: " + str(e))
