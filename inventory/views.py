from rest_framework.views import APIView

from core.authorization import Permission, require_permission
from core.decorators import forge
from core.utils import model_unwrap
from inventory.serializers import CardPurchaseSerializer, CardQueryParams, CardSerializer, CardSimilarityParams, VendorSerializer
from inventory.services import CardService, VendorService


class VendorView(APIView):
    @forge
    @require_permission(Permission.VENDOR_CREATE)
    def post(self, request):
        body = VendorSerializer.validate_request(request)

        VendorService.create_vendor(name=body.get_value("name"), phone=body.get_value("phone"))

        return {"message": "Vendor created successfully"}


class CardView(APIView):
    @forge
    @require_permission(Permission.CARD_READ)
    def get(self, request, card_id=None):
        if card_id:
            card = CardService.get_card_by_id(card_id)
            return model_unwrap(card)

        params = CardQueryParams.validate_params(request)
        card = CardService.get_card_by_id(params.get_value("card_id"))
        return model_unwrap(card)

    @forge
    @require_permission(Permission.CARD_CREATE)
    def post(self, request):
        body = CardSerializer.validate_request(request)

        CardService.create_card(
            vendor_id=body.get_value("vendor_id"),
            staff=request.staff,
            image=body.get_value("image"),
            cost_price=body.get_value("cost_price"),
            base_price=body.get_value("base_price"),
            max_discount=body.get_value("max_discount"),
            quantity=body.get_value("quantity"),
        )

        return {"message": "Card created successfully"}


class CardSimilarityView(APIView):
    @forge
    def get(self, request):
        params = CardSimilarityParams.validate_params(request)

        cards = CardService.find_similar_cards(params.get_value("image"))
        return model_unwrap(cards)


class CardPurchaseView(APIView):
    @forge
    @require_permission(Permission.CARD_UPDATE)
    def patch(self, request, card_id):
        body = CardPurchaseSerializer.validate_request(request)

        quantity = body.get_value("quantity")

        CardService.purchase_additional_stock(card_id=card_id, quantity_change=quantity, staff=request.staff)

        return {"message": "Card stock purchased successfully"}
