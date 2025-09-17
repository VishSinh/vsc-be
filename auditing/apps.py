from django.apps import AppConfig


class AuditingConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "auditing"

    def ready(self) -> None:
        import auditing.signals  # noqa: F401

        super().ready()
