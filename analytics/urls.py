from django.urls import path

from analytics.views import DashboardView, DetailedAnalyticsView

urlpatterns = [
    path("dashboard/", DashboardView.as_view(), name="dashboard"),
    path("analytics/detail/", DetailedAnalyticsView.as_view(), name="detailed_analytics"),
]
