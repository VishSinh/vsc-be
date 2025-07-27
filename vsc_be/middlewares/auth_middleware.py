from django.conf import settings
from rest_framework import status

from accounts.models import Staff
from core.exceptions import InternalServerError, Unauthorized
from core.helpers.api_response import APIResponse
from core.helpers.security import Security
import logging

logger = logging.getLogger(__name__)

class AuthMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        self.skip_auth_patterns = getattr(settings, 'SKIP_AUTH_PATTERNS', [])

    def __call__(self, request):
        try:
            if any(pattern in request.path for pattern in self.skip_auth_patterns):
                return self.get_response(request)
            
            auth_header = request.headers.get('Authorization')
            if not auth_header or not auth_header.startswith('Bearer '):
                raise Unauthorized('Authentication credentials were not provided')
            
            token = auth_header.split(' ')[1]
            
            try:
                staff_id, expiry = Security.verify_token(token)
            except ValueError as e:
                raise Unauthorized(str(e))
            
            staff = Staff.objects.filter(id=staff_id).first()
            if not staff:
                raise Unauthorized('Invalid user')
            
            request.user_obj = staff
            
            return self.get_response(request)
        except Unauthorized as e:
            return APIResponse(success=False, status_code=status.HTTP_401_UNAUTHORIZED, error=str(e)).response()
        except Exception as e:
            logger.error(f"Auth middleware error: {str(e)}")
            return APIResponse(success=False, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, error=str(e)).response()
            