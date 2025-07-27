from datetime import timedelta
from passlib.context import CryptContext
from jose import jwt
from django.conf import settings
from django.utils import timezone

from core.exceptions import InternalServerError, Unauthorized


class Security:
    _pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

    @staticmethod
    def get_password_hash(password: str) -> str:
        return Security._pwd_context.hash(password)
    
    @staticmethod
    def verify_password(password: str, hashed_password: str) -> bool:
        return Security._pwd_context.verify(password, hashed_password)
    
    @staticmethod
    def create_token(data: dict) -> str:
        data['exp'] = timezone.now() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        return jwt.encode(data, settings.TOKEN_SECRET, algorithm=settings.ALGORITHM)
    
    @staticmethod
    def verify_token(token: str) -> tuple:
        try:
            decoded_token = jwt.decode(token, settings.SESSION_SECRET_KEY, algorithms=['HS256'])
            staff_id = decoded_token.get('staff_id')
            expiry = timezone.datetime.fromtimestamp(decoded_token.get('exp'), tz=timezone.utc)
            
            if expiry < timezone.now():
                raise Unauthorized('Token expired')
            
            return staff_id, expiry
        except jwt.ExpiredSignatureError:
            raise Unauthorized('Token expired')
        except jwt.InvalidTokenError:
            raise Unauthorized('Invalid Token')
        except Exception as e:
            raise InternalServerError('Error verifying token')
    
    