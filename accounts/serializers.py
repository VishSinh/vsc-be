from rest_framework import serializers

from accounts.models import Staff
from core.constants import SERIALIZER_MAX_NAME_LENGTH, SERIALIZER_MAX_PHONE_LENGTH, SERIALIZER_MIN_NAME_LENGTH, SERIALIZER_MIN_PHONE_LENGTH
from core.helpers.base_serializer import BaseSerializer
from core.helpers.param_serializer import ParamSerializer


# Parameter Serializers
class CustomerQueryParams(ParamSerializer):
    phone = serializers.CharField(required=True, min_length=SERIALIZER_MIN_PHONE_LENGTH, max_length=SERIALIZER_MAX_PHONE_LENGTH)


# Request Serializers
class RegisterSerializer(BaseSerializer):
    name = serializers.CharField(required=True, min_length=SERIALIZER_MIN_NAME_LENGTH, max_length=SERIALIZER_MAX_NAME_LENGTH)
    phone = serializers.CharField(required=True, min_length=SERIALIZER_MIN_PHONE_LENGTH, max_length=SERIALIZER_MAX_PHONE_LENGTH)
    password = serializers.CharField(required=True, min_length=8)
    role = serializers.ChoiceField(required=True, choices=Staff.Role.choices)


class LoginSerializer(BaseSerializer):
    phone = serializers.CharField(required=True, min_length=SERIALIZER_MIN_PHONE_LENGTH, max_length=SERIALIZER_MAX_PHONE_LENGTH)
    password = serializers.CharField(required=True, min_length=8)


class CustomerCreateSerializer(BaseSerializer):
    name = serializers.CharField(required=True, min_length=SERIALIZER_MIN_NAME_LENGTH, max_length=SERIALIZER_MAX_NAME_LENGTH)
    phone = serializers.CharField(required=True, min_length=SERIALIZER_MIN_PHONE_LENGTH, max_length=SERIALIZER_MAX_PHONE_LENGTH)
