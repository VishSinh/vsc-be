from rest_framework.views import APIView

from auditing.models import APIAuditLog, ModelAuditLog
from auditing.serializers import AuditLogQueryParams
from core.authorization import Permission, require_permission
from core.decorators import forge
from core.helpers.pagination import PaginationHelper
from core.utils import model_unwrap


class ModelAuditLogListView(APIView):
    @forge
    @require_permission(Permission.AUDIT_READ)
    def get(self, request):
        params = AuditLogQueryParams.validate_params(request)

        queryset = ModelAuditLog.objects.all()

        # Filters
        if staff_id := params.get_value("staff_id"):
            queryset = queryset.filter(staff_id=staff_id)
        if request_id := params.get_value("request_id"):
            queryset = queryset.filter(request_id=request_id)
        if action := params.get_value("action"):
            queryset = queryset.filter(action=action)
        if model_name := params.get_value("model_name"):
            queryset = queryset.filter(model_name=model_name)
        if start := params.get_value("start"):
            queryset = queryset.filter(created_at__gte=start)
        if end := params.get_value("end"):
            queryset = queryset.filter(created_at__lte=end)

        data, pagination = PaginationHelper.paginate_queryset(
            queryset=queryset,
            page=params.get_value("page"),
            page_size=params.get_value("page_size"),
        )

        return model_unwrap(data, include_timestamps=True), pagination


class APIAuditLogListView(APIView):
    @forge
    @require_permission(Permission.AUDIT_READ)
    def get(self, request):
        params = AuditLogQueryParams.validate_params(request)

        queryset = APIAuditLog.objects.all()

        # Filters
        if staff_id := params.get_value("staff_id"):
            queryset = queryset.filter(staff_id=staff_id)
        if request_id := params.get_value("request_id"):
            queryset = queryset.filter(request_id=request_id)
        if endpoint := params.get_value("endpoint"):
            queryset = queryset.filter(endpoint=endpoint)
        if status_code := params.get_value("status_code"):
            queryset = queryset.filter(status_code=status_code)
        if start := params.get_value("start"):
            queryset = queryset.filter(created_at__gte=start)
        if end := params.get_value("end"):
            queryset = queryset.filter(created_at__lte=end)

        data, pagination = PaginationHelper.paginate_queryset(
            queryset=queryset,
            page=params.get_value("page"),
            page_size=params.get_value("page_size"),
        )

        return model_unwrap(data, include_timestamps=True), pagination
