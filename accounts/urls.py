from django.urls import path

from accounts.views import LoginView, RegisterView

app_name = "accounts"

urlpatterns = [
    # Authentication endpoints
    path("login/", LoginView.as_view(), name="login"),
    path("register/", RegisterView.as_view(), name="register"),
]
