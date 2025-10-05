from rest_framework import serializers

from accounts.models import Staff
from core.constants import (
    PAGINATION_DEFAULT_PAGE,
    PAGINATION_DEFAULT_PAGE_SIZE,
    SERIALIZER_MAX_NAME_LENGTH,
    SERIALIZER_MAX_PHONE_LENGTH,
    SERIALIZER_MIN_NAME_LENGTH,
    SERIALIZER_MIN_PHONE_LENGTH,
)
from core.helpers.base_serializer import BaseSerializer
from core.helpers.param_serializer import ParamSerializer
from core.helpers.query_params import BaseListParams


# Parameter Serializers
class CustomerQueryParams(BaseListParams):
    phone = serializers.CharField(required=False, min_length=SERIALIZER_MIN_PHONE_LENGTH, max_length=SERIALIZER_MAX_PHONE_LENGTH)


class StaffQueryParams(ParamSerializer):
    page = serializers.IntegerField(required=False, default=PAGINATION_DEFAULT_PAGE)
    page_size = serializers.IntegerField(required=False, default=PAGINATION_DEFAULT_PAGE_SIZE)


# Request Serializers
class RegisterSerializer(BaseSerializer):
    name = serializers.CharField(required=True, min_length=SERIALIZER_MIN_NAME_LENGTH, max_length=SERIALIZER_MAX_NAME_LENGTH)
    phone = serializers.CharField(required=True, min_length=SERIALIZER_MIN_PHONE_LENGTH, max_length=SERIALIZER_MAX_PHONE_LENGTH)
    password = serializers.CharField(required=True, min_length=3)
    role = serializers.ChoiceField(required=True, choices=Staff.Role.choices)


class LoginSerializer(BaseSerializer):
    phone = serializers.CharField(required=True, min_length=SERIALIZER_MIN_PHONE_LENGTH, max_length=SERIALIZER_MAX_PHONE_LENGTH)
    password = serializers.CharField(required=True, min_length=3)


class CustomerCreateSerializer(BaseSerializer):
    name = serializers.CharField(required=True, min_length=SERIALIZER_MIN_NAME_LENGTH, max_length=SERIALIZER_MAX_NAME_LENGTH)
    phone = serializers.CharField(required=True, min_length=SERIALIZER_MIN_PHONE_LENGTH, max_length=SERIALIZER_MAX_PHONE_LENGTH)


class CustomerUpdateSerializer(BaseSerializer):
    name = serializers.CharField(required=False, min_length=SERIALIZER_MIN_NAME_LENGTH, max_length=SERIALIZER_MAX_NAME_LENGTH)
    phone = serializers.CharField(required=False, min_length=SERIALIZER_MIN_PHONE_LENGTH, max_length=SERIALIZER_MAX_PHONE_LENGTH)
