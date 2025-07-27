from rest_framework.views import APIView

from accounts.serializers import LoginSerializer, RegisterSerializer
from accounts.services import StaffService
from core.decorators import forge
from core.authorization import Permission, require_permission


class RegisterView(APIView):

    @forge
    @require_permission(Permission.ACCOUNT_CREATE)
    def post(self, request):    
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        StaffService.create_staff(
            name=serializer.get_value('name'),
            phone=serializer.get_value('phone'),
            password=serializer.get_value('password'),
            role=serializer.get_value('role')
        )

        return {'message': 'Registration successful'}
        

class LoginView(APIView):

    @forge
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        token = StaffService.authenticate_staff_and_get_token(
            phone=serializer.get_value('phone'),
            password=serializer.get_value('password')
        )
        
        return {
            'message': 'Login successful',
            'token': token
        }