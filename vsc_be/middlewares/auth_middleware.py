import logging

from django.conf import settings
from rest_framework import status

from accounts.services import StaffService
from core.exceptions import Unauthorized
from core.helpers.api_response import APIResponse
from core.helpers.security import Security

logger = logging.getLogger(__name__)


class AuthMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        self.skip_auth_patterns = getattr(settings, "SKIP_AUTH_PATTERNS", [])

    def __call__(self, request):
        try:
            if any(pattern in request.path for pattern in self.skip_auth_patterns):
                return self.get_response(request)

            auth_header = request.headers.get("Authorization")
            if not auth_header or not auth_header.startswith("Bearer "):
                raise Unauthorized("Authentication credentials were not provided")

            token = auth_header.split(" ")[1]

            staff_id, expiry = Security.verify_token(token)
            staff = StaffService.get_staff_by_id(staff_id)

            if not staff:
                raise Unauthorized("Invalid Staff")

            request.staff = staff
            request.is_authenticated = True

            return self.get_response(request)
        except Unauthorized as e:
            print(e)
            return APIResponse(success=False, status_code=status.HTTP_401_UNAUTHORIZED, error=e).response()
        except Exception as e:
            print(f"Auth middleware error: {str(e)}")
            return APIResponse(
                success=False,
                status_code=status.HTTP_401_UNAUTHORIZED,
                error=e,
            ).response()
