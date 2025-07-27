from django.urls import path

from orders.views import OrderView

app_name = "orders"

urlpatterns = [
    path("orders/", OrderView.as_view(), name="order"),
    path("orders/<uuid:order_id>/", OrderView.as_view(), name="order_detail"),
]
