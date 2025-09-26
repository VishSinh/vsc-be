from rest_framework.views import APIView

from accounts.serializers import CustomerCreateSerializer, CustomerQueryParams, LoginSerializer, RegisterSerializer
from accounts.services import CustomerService, StaffService
from core.authorization import AuthorizationService, Permission, require_permission
from core.decorators import forge
from core.utils import model_unwrap


class RegisterView(APIView):
    @forge
    @require_permission(Permission.ACCOUNT_CREATE)
    def post(self, request):
        body = RegisterSerializer.validate_request(request)

        StaffService.create_staff(
            name=body.get_value("name"),
            phone=body.get_value("phone"),
            password=body.get_value("password"),
            role=body.get_value("role"),
        )

        return {"message": "Registration successful"}


class LoginView(APIView):
    @forge
    def post(self, request):
        body = LoginSerializer.validate_request(request)

        staff = StaffService.get_staff_by_phone(body.get_value("phone"))

        token = StaffService.authenticate_staff_and_get_token(staff=staff, password=body.get_value("password"))

        return {"message": "Login successful", "token": token, "role": staff.role}


class CustomerView(APIView):
    @forge
    @require_permission(Permission.CUSTOMER_READ)
    def get(self, request, customer_id=None):
        if customer_id:
            customer = CustomerService.get_customer_by_id(customer_id)
            return model_unwrap(customer)

        params = CustomerQueryParams.validate_params(request)
        customer = CustomerService.get_customer_by_phone(params.get_value("phone"))
        return model_unwrap(customer)

    @forge
    @require_permission(Permission.CUSTOMER_CREATE)
    def post(self, request):
        body = CustomerCreateSerializer.validate_request(request)

        CustomerService.create_customer(name=body.get_value("name"), phone=body.get_value("phone"))

        return {"message": "Customer created successfully"}


class PermissionsView(APIView):
    """API to get all available permissions"""

    @forge
    @require_permission(Permission.SYSTEM_CONFIG)
    def get(self, request):
        """Get all available permissions in the system"""
        # Get all permission constants from the Permission class
        permissions = []
        for name, value in Permission.__dict__.items():
            if not name.startswith("__") and not callable(value) and isinstance(value, str):
                permissions.append({"name": name, "value": value, "description": name.replace("_", " ").title()})

        return {"permissions": permissions, "total_count": len(permissions)}


class CurrentStaffPermissionsView(APIView):
    """API to get current staff member's permissions"""

    @forge
    def get(self, request):
        """Get current staff member's permissions"""
        # Get the current staff from request (set by auth middleware)
        staff = getattr(request, "staff", None)

        if not staff:
            return {"error": "No authenticated staff found"}, 401

        # Get staff permissions using AuthorizationService
        permissions = AuthorizationService.get_user_permissions(staff)

        return {"staff_id": str(staff.id), "staff_role": staff.role, "permissions": permissions, "total_count": len(permissions)}
