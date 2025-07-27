from django.urls import path

from inventory.views import CardView, VendorView


app_name = 'inventory'

urlpatterns = [
    path('vendors/', VendorView.as_view(), name='vendor'),
    path('cards/', CardView.as_view(), name='card'),
]