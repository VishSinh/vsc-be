from django.urls import path

from orders.views import BillAdjustmentView, BillView, OrderView, PaymentView

app_name = "orders"

urlpatterns = [
    path("orders/", OrderView.as_view(), name="order"),
    path("orders/<uuid:order_id>/", OrderView.as_view(), name="order_detail"),
    path("bills/", BillView.as_view(), name="bill"),
    path("bills/<uuid:bill_id>/", BillView.as_view(), name="bill_detail"),
    path("payments/", PaymentView.as_view(), name="payment"),
    path("payments/<uuid:payment_id>/", PaymentView.as_view(), name="payment_detail"),
    path("bill-adjustments/", BillAdjustmentView.as_view(), name="bill_adjustment"),
    path("bill-adjustments/<uuid:adjustment_id>/", BillAdjustmentView.as_view(), name="bill_adjustment_detail"),
]
