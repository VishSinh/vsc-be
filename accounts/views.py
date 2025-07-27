from rest_framework.views import APIView

from accounts.serializers import CustomerCreateSerializer, CustomerQueryParams, LoginSerializer, RegisterSerializer
from accounts.services import CustomerService, StaffService
from core.authorization import Permission, require_permission
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

        return {"message": "Login successful", "token": token}


class CustomerView(APIView):
    @forge
    @require_permission(Permission.CUSTOMER_READ)
    def get(self, request):
        params = CustomerQueryParams.validate_params(request)

        customer = CustomerService.get_customer_by_phone(params.get_value("phone"))
        return model_unwrap(customer)

    @forge
    @require_permission(Permission.CUSTOMER_CREATE)
    def post(self, request):
        body = CustomerCreateSerializer.validate_request(request)

        CustomerService.create_customer(name=body.get_value("name"), phone=body.get_value("phone"))

        return {"message": "Customer created successfully"}
