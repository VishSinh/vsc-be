from typing import Any, Dict, Set

from django.conf import settings


def model_label(sender) -> str:
    return f"{sender._meta.app_label}.{sender.__name__}"


def get_ignore_fields(sender) -> Set[str]:
    base = {"created_at", "updated_at", "last_login"}
    cfg = getattr(settings, "AUDIT_FIELD_IGNORE", {})
    return base | set(cfg.get("*", [])) | set(cfg.get(model_label(sender), []))


def is_audited_model(sender) -> bool:
    if sender._meta.app_label == "auditing":
        return False
    include = set(getattr(settings, "AUDIT_INCLUDE_APPS", []))
    exclude_apps = set(getattr(settings, "AUDIT_EXCLUDE_APPS", []))
    exclude_models = set(getattr(settings, "AUDIT_EXCLUDE_MODELS", ["auditing.ModelAuditLog", "auditing.APIAuditLog"]))
    if include and sender._meta.app_label not in include:
        return False
    if sender._meta.app_label in exclude_apps:
        return False
    return model_label(sender) not in exclude_models


def normalize_value(value: Any) -> Any:
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def instance_state(instance) -> Dict[str, Any]:
    ignores = get_ignore_fields(type(instance))
    return {
        f.name: normalize_value(getattr(instance, getattr(f, "attname", f.name))) for f in instance._meta.concrete_fields if f.name not in ignores
    }


def diff(old: Dict[str, Any], new: Dict[str, Any]):
    keys = set(old) | set(new)
    changed = [k for k in keys if old.get(k) != new.get(k)]
    return {k: old.get(k) for k in changed if k in old}, {k: new.get(k) for k in changed if k in new}
