from django.urls import path

from auditing.views import APIAuditLogListView, ModelAuditLogListView


app_name = "auditing"


urlpatterns = [
    path("audit/model-logs/", ModelAuditLogListView.as_view(), name="model_audit_logs"),
    path("audit/api-logs/", APIAuditLogListView.as_view(), name="api_audit_logs"),
]


