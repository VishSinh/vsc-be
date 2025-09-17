import uuid

from django.db import models

from accounts.models import Staff
from core.constants import ACTION_LENGTH, LONG_TEXT_LENGTH, MODEL_NAME_LENGTH, TEXT_LENGTH


class ModelAuditLog(models.Model):
    class Action(models.TextChoices):
        CREATE = "CREATE", "Create"
        UPDATE = "UPDATE", "Update"
        DELETE = "DELETE", "Delete"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    staff = models.ForeignKey(Staff, on_delete=models.CASCADE, related_name="model_audit_logs")
    model_name = models.CharField(max_length=MODEL_NAME_LENGTH)
    model_id = models.UUIDField()
    action = models.CharField(max_length=ACTION_LENGTH, choices=Action.choices)
    old_values = models.JSONField(default=dict, blank=True)
    new_values = models.JSONField(default=dict, blank=True)
    # Metadata
    request_id = models.UUIDField(null=True, blank=True)
    actor_ip = models.GenericIPAddressField(null=True, blank=True)
    actor_user_agent = models.CharField(max_length=LONG_TEXT_LENGTH, blank=True)
    notes = models.TextField(blank=True)

    class Source(models.TextChoices):
        API = "API", "API"
        JOB = "JOB", "Job"
        ADMIN = "ADMIN", "Admin"
        SYSTEM = "SYSTEM", "System"

    source = models.CharField(max_length=ACTION_LENGTH, choices=Source.choices, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "model_audit_logs"
        verbose_name = "Model Audit Log"
        verbose_name_plural = "Model Audit Logs"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["model_name", "model_id", "created_at"], name="idx_mal_model_time"),
            models.Index(fields=["staff", "created_at"], name="idx_mal_staff_time"),
            models.Index(fields=["action", "created_at"], name="idx_mal_action_time"),
        ]

    def __str__(self):
        return f"{self.action} on {self.model_name} by {self.staff.name}"


class APIAuditLog(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    staff = models.ForeignKey(Staff, on_delete=models.SET_NULL, related_name="api_audit_logs", null=True, blank=True)
    endpoint = models.CharField(max_length=TEXT_LENGTH)
    request_method = models.CharField(max_length=TEXT_LENGTH)
    request_body = models.JSONField(default=dict, blank=True)
    response_body = models.JSONField(default=dict, blank=True)
    status_code = models.IntegerField(null=True, blank=True)
    duration_ms = models.IntegerField(null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=LONG_TEXT_LENGTH, blank=True)
    query_params = models.JSONField(default=dict, blank=True)
    headers = models.JSONField(default=dict, blank=True)
    request_id = models.UUIDField(null=True, blank=True)
    response_size_bytes = models.IntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "api_audit_logs"
        verbose_name = "API Audit Log"
        verbose_name_plural = "API Audit Logs"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["endpoint", "request_method", "created_at"], name="idx_aal_endpoint_method_time"),
            models.Index(fields=["status_code", "created_at"], name="idx_aal_status_time"),
            models.Index(fields=["staff", "created_at"], name="idx_aal_staff_time"),
        ]

    def __str__(self):
        staff_name = self.staff.name if self.staff else "anonymous"
        return f"{self.request_method} {self.endpoint} by {staff_name}"
