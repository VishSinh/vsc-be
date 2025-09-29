from django.urls import path

from inventory.views import CardDetailView, CardPurchaseView, CardSimilarityView, CardView, VendorView

app_name = "inventory"

urlpatterns = [
    path("vendors/", VendorView.as_view(), name="vendor"),
    path("vendors/<uuid:vendor_id>/", VendorView.as_view(), name="vendor"),
    path("cards/", CardView.as_view(), name="card"),
    path("cards/<uuid:card_id>/", CardView.as_view(), name="card"),
    path("cards/<uuid:card_id>/detail/", CardDetailView.as_view(), name="card-detail"),
    path("cards/similar/", CardSimilarityView.as_view(), name="card-similarity"),
    path(
        "cards/<uuid:card_id>/purchase/",
        CardPurchaseView.as_view(),
        name="card-purchase",
    ),
]
