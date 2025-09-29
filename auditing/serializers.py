from rest_framework import serializers

from core.constants import PAGINATION_DEFAULT_PAGE, PAGINATION_DEFAULT_PAGE_SIZE
from core.helpers.param_serializer import ParamSerializer


class AuditLogQueryParams(ParamSerializer):
    page = serializers.IntegerField(required=False, min_value=1, default=PAGINATION_DEFAULT_PAGE)
    page_size = serializers.IntegerField(required=False, min_value=1, max_value=100, default=PAGINATION_DEFAULT_PAGE_SIZE)
    # Optional filters
    staff_id = serializers.UUIDField(required=False)
    request_id = serializers.UUIDField(required=False)
    start = serializers.DateTimeField(required=False)
    end = serializers.DateTimeField(required=False)
    action = serializers.CharField(required=False)
    model_name = serializers.CharField(required=False)
    endpoint = serializers.CharField(required=False)
    status_code = serializers.IntegerField(required=False)
