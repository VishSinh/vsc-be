from rest_framework import serializers

from accounts.models import Staff
from core.helpers.base_serializer import BaseSerializer


class RegisterSerializer(BaseSerializer):
    name = serializers.CharField(required=True, min_length=3, max_length=100)
    phone = serializers.CharField(required=True, min_length=10, max_length=10)
    password = serializers.CharField(required=True, min_length=8)
    role = serializers.ChoiceField(required=True, choices=Staff.Role.choices)


class LoginSerializer(BaseSerializer):
    phone = serializers.CharField(required=True, min_length=10, max_length=10)
    password = serializers.CharField(required=True, min_length=8)
