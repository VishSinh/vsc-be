from django.urls import path

from accounts.views import CurrentStaffPermissionsView, CustomerView, LoginView, PermissionsView, RegisterView

app_name = "accounts"

urlpatterns = [
    # Authentication endpoints
    path("auth/login/", LoginView.as_view(), name="login"),
    path("auth/register/", RegisterView.as_view(), name="register"),
    # Customer endpoints
    path("customers/", CustomerView.as_view(), name="customers"),
    # Permission endpoints
    path("permissions/", CurrentStaffPermissionsView.as_view(), name="permissions_current"),
    path("permissions/all/", PermissionsView.as_view(), name="permissions_all"),
]
