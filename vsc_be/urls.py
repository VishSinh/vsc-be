from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path

from decouple import config


def health_view(request):
    return JsonResponse({"status": "ok"})


urlpatterns = [
    path("admin/", admin.site.urls),
    # API v1 endpoints
    path(
        "api/v1/",
        include(
            [
                path("health/", health_view),
                path("", include("accounts.urls")),
                path("", include("inventory.urls")),
                path("", include("orders.urls")),
                path("", include("production.urls")),
                path("", include("analytics.urls")),
                path("", include("auditing.urls")),
            ]
        ),
    ),
]

# Optionally expose Prometheus metrics when enabled
try:
    if config("ENABLE_PROMETHEUS", default=False, cast=bool):
        urlpatterns.append(path("", include("django_prometheus.urls")))
except Exception:
    pass

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
