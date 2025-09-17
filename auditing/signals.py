from django.db.models.signals import post_save, pre_delete, pre_save
from django.dispatch import receiver

from auditing.context import get_current_staff
from auditing.models import ModelAuditLog
from auditing.utils import diff, instance_state, is_audited_model


@receiver(pre_save)
def _audit_pre_save(sender, instance, **kwargs):
    if not is_audited_model(sender):
        return
    if getattr(instance, "pk", None) and sender.objects.filter(pk=instance.pk).exists():
        instance.__audit_old = instance_state(sender.objects.get(pk=instance.pk))
    else:
        instance.__audit_old = None


@receiver(post_save)
def _audit_post_save(sender, instance, created: bool, **kwargs):
    if not is_audited_model(sender):
        return
    old_values = getattr(instance, "__audit_old", None) or {}
    new_values = instance_state(instance)
    staff = get_current_staff()
    if created:
        ModelAuditLog.objects.create(
            staff=staff, model_name=sender._meta.label, model_id=instance.pk, action=ModelAuditLog.Action.CREATE, old_values={}, new_values=new_values
        )
        return
    old_diff, new_diff = diff(old_values, new_values)
    if not old_diff and not new_diff:
        return
    ModelAuditLog.objects.create(
        staff=staff, model_name=sender._meta.label, model_id=instance.pk, action=ModelAuditLog.Action.UPDATE, old_values=old_diff, new_values=new_diff
    )


@receiver(pre_delete)
def _audit_pre_delete(sender, instance, **kwargs):
    if not is_audited_model(sender):
        return
    ModelAuditLog.objects.create(
        staff=get_current_staff(),
        model_name=sender._meta.label,
        model_id=instance.pk,
        action=ModelAuditLog.Action.DELETE,
        old_values=instance_state(instance),
        new_values={},
    )
