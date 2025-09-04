from rest_framework.views import APIView

from core.authorization import Permission, require_permission
from core.decorators import forge
from core.exceptions import BadRequest
from core.helpers.image_upload import ImageUpload
from core.helpers.image_utils import ImageUtils
from core.helpers.pagination import PaginationHelper
from core.utils import model_unwrap
from inventory.serializers import (
    CardPurchaseSerializer,
    CardQueryParams,
    CardSerializer,
    CardSimilaritySerializer,
    CardUpdateSerializer,
    VendorQueryParams,
    VendorSerializer,
)
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
        vendors = VendorService.get_vendors()
        vendors, page_info = PaginationHelper.paginate_queryset(vendors, params.get_value("page"), params.get_value("page_size"))

        return [model_unwrap(vendor) for vendor in vendors], page_info

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

        if params.get_value("barcode"):
            card = CardService.get_card_by_barcode(params.get_value("barcode"))
            return model_unwrap(card)

        cards = CardService.get_cards()
        cards, page_info = PaginationHelper.paginate_queryset(cards, params.get_value("page"), params.get_value("page_size"))

        return [model_unwrap(card) for card in cards], page_info

    @forge
    @require_permission(Permission.CARD_CREATE)
    def post(self, request):
        body = CardSerializer.validate_request(request)

        image = request.FILES.get("image")
        if not image:
            raise BadRequest("Image is required")

        perceptual_hash = ImageUtils.generate_perceptual_hash(image)

        image_url = ImageUpload.upload_image_and_get_url(image)

        card = CardService.create_card(
            vendor_id=body.get_value("vendor_id"),
            staff=request.staff,
            image_url=image_url,
            cost_price=body.get_value("cost_price"),
            sell_price=body.get_value("sell_price"),
            max_discount=body.get_value("max_discount"),
            quantity=body.get_value("quantity"),
            perceptual_hash=perceptual_hash,
        )

        to_return = model_unwrap(card)
        to_return["message"] = "Card created successfully"

        return to_return

    @forge
    @require_permission(Permission.CARD_UPDATE)
    def patch(self, request, card_id):
        body = CardUpdateSerializer.validate_request(request)

        updates = {"image": request.FILES.get("image"), **body.validated_data}

        card = CardService.update_card(card_id, **updates)

        to_return = model_unwrap(card)
        to_return["message"] = "Card updated successfully"
        return to_return

    @forge
    @require_permission(Permission.CARD_DELETE)
    def delete(self, request, card_id):
        CardService.deactivate_card(card_id)
        return {"message": "Card deleted successfully"}


class CardSimilarityView(APIView):
    @forge
    def post(self, request):
        CardSimilaritySerializer.validate_request(request)

        image = request.FILES.get("image")
        if not image:
            raise BadRequest("Image is required")

        cards = CardService.find_similar_cards(image)
        return model_unwrap(cards)


class CardPurchaseView(APIView):
    @forge
    @require_permission(Permission.CARD_PURCHASE)
    def patch(self, request, card_id):
        body = CardPurchaseSerializer.validate_request(request)

        quantity = body.get_value("quantity")

        CardService.purchase_additional_stock(card_id=card_id, quantity_change=quantity, staff=request.staff)

        return {"message": "Card stock purchased successfully"}
