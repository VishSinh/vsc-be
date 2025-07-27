import uuid
from django.db import models
from accounts.models import Staff
from core.constants import ACTION_LENGTH, TABLE_NAME_LENGTH


class AuditLog(models.Model):
    """Records a log of significant changes made by staff in the system"""
    class Action(models.TextChoices):
        CREATE = 'CREATE', 'Create'
        UPDATE = 'UPDATE', 'Update'
        DELETE = 'DELETE', 'Delete'
        LOGIN = 'LOGIN', 'Login'
        LOGOUT = 'LOGOUT', 'Logout'
        EXPORT = 'EXPORT', 'Export'
        IMPORT = 'IMPORT', 'Import'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    staff = models.ForeignKey(Staff, on_delete=models.CASCADE, related_name='audit_logs')
    table_name = models.CharField(max_length=TABLE_NAME_LENGTH)
    record_id = models.UUIDField()
    action = models.CharField(max_length=ACTION_LENGTH, choices=Action.choices)
    old_values = models.TextField(blank=True, null=True)
    new_values = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'audit_logs'
        verbose_name = 'Audit Log'
        verbose_name_plural = 'Audit Logs'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.action} on {self.table_name} by {self.staff.name}"
