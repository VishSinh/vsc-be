
from rest_framework import APIView

from accounts.models import Staff
from accounts.serializers import LoginSerializer, RegisterSerializer
from core.decorators import forge
from core.exceptions import Unauthorized
from core.helpers.security import Security
from core.authorization import Permission, require_permission
from core.utils import model_unwrap


class RegisterView(APIView):


    @forge
    @require_permission(Permission.ACCOUNT_CREATE)
    def post(self, request):    
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        name = serializer.get_value('name')
        phone = serializer.get_value('phone')
        password = serializer.get_value('password')
        role = serializer.get_value('role')

        hashed_password = Security.get_password_hash(password)

        staff = Staff.objects.create(name=name, phone=phone, password=hashed_password, role=role)

        return model_unwrap(staff), 201
        
    

class LoginView(APIView):

    @forge
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        phone = serializer.get_value('phone')
        password = serializer.get_value('password')

        staff = Staff.objects.filter(phone=phone).first()
        if not staff:
            raise Unauthorized('Invalid phone or password')
        
        if not Security.verify_password(password, staff.password):
            raise Unauthorized('Invalid phone or password')
        
        token = Security.create_token({'staff_id': staff.id, 'role': staff.role})
        
        return {
            'message': 'Login successful',
            'token': token
        }