from rest_framework.views import APIView

from core.utils import model_unwrap
from inventory.models import Vendor, Card
from inventory.serializers import CardSerializer, CardPurchaseSerializer, VendorSerializer
from inventory.services import CardService, VendorService
from core.decorators import forge
from core.authorization import Permission, require_permission
from core.exceptions import ResourceNotFound


class VendorView(APIView):

    @forge
    @require_permission(Permission.VENDOR_CREATE)
    def post(self, request):
        serializer = VendorSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        name = serializer.get_value('name')
        phone = serializer.get_value('phone')

        VendorService.create_vendor(name=name, phone=phone)

        return {'message': 'Vendor created successfully'}



class CardView(APIView):

    @forge
    @require_permission(Permission.CARD_READ)
    def get(self, request, card_id=None):
        if card_id:
            card = Card.objects.filter(id=card_id).first()
            if not card:
                raise ResourceNotFound('Card not found')

            return model_unwrap(card)

        return model_unwrap(Card.objects.all())


    @forge
    @require_permission(Permission.CARD_CREATE)
    def post(self, request):
        serializer = CardSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        CardService.create_card(
            vendor_id=serializer.get_value('vendor_id'),
            staff=request.staff,
            image=serializer.get_value('image'),
            cost_price=serializer.get_value('cost_price'),
            base_price=serializer.get_value('base_price'),
            max_discount=serializer.get_value('max_discount'),
            quantity=serializer.get_value('quantity')
        )
        
        return {'message': 'Card created successfully'}


class CardSimilarityView(APIView):
    
    @forge
    def get(self, request):
        image = request.query_params.get('image')
        cards = CardService.find_similar_cards(image)

        return model_unwrap(cards)
        

class CardPurchaseView(APIView):

    @forge
    def post(self, request, card_id):
        serializer = CardPurchaseSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        quantity = serializer.get_value('quantity')

        CardService.purchase_additional_stock(
            card_id=card_id,
            quantity_change=quantity,
            staff=request.staff
        )

        return {'message': 'Card stock purchased successfully'}




        
