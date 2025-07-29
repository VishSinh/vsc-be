from rest_framework.views import APIView

from core.authorization import Permission, require_permission
from core.decorators import forge
from core.helpers.pagination import PaginationHelper
from core.utils import model_unwrap
from inventory.serializers import CardPurchaseSerializer, CardQueryParams, CardSerializer, CardSimilarityParams, VendorQueryParams, VendorSerializer
from inventory.services import CardService, VendorService


class VendorView(APIView):
    @forge
    @require_permission(Permission.VENDOR_READ)
    def get(self, request, vendor_id=None):
        if vendor_id:
            vendor = VendorService.get_vendor_by_id(vendor_id)
            return model_unwrap(vendor)

        params = VendorQueryParams.validate_params(request)

        # Get all vendors with pagination
        page = params.get_value("page")
        page_size = params.get_value("page_size")
        paginated_response = VendorService.get_vendors(page=page, page_size=page_size)

        # Convert the data using model_unwrap
        paginated_response["items"] = [model_unwrap(vendor) for vendor in paginated_response["items"]]

        return paginated_response

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

        cards = CardService.get_cards()
        cards, page_info = PaginationHelper.paginate_queryset(cards, params.get_value("page"), params.get_value("page_size"))

        return [model_unwrap(card) for card in cards], page_info

    @forge
    @require_permission(Permission.CARD_CREATE)
    def post(self, request):
        body = CardSerializer.validate_request(request)

        CardService.create_card(
            vendor_id=body.get_value("vendor_id"),
            staff=request.staff,
            image=body.get_value("image"),
            cost_price=body.get_value("cost_price"),
            sell_price=body.get_value("sell_price"),
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
