import requests
from PIL import Image
from io import BytesIO
import imagehash
from rest_framework.views import APIView

from inventory.models import Vendor, Card
from inventory.serializers import CardSerializer, VendorSerializer
from core.decorators import forge
from core.authorization import Permission, require_permission
from core.exceptions import InternalServerError


class VendorView(APIView):

    @forge
    @require_permission(Permission.VENDOR_CREATE)
    def post(self, request):
        serializer = VendorSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        name = serializer.get_value('name')
        phone = serializer.get_value('phone')

        Vendor.objects.create(name=name, phone=phone)

        return {'message': 'Vendor created successfully'}



class CardView(APIView):

    @staticmethod
    def generate_perceptual_hash(image_url: str):
        response = requests.get(image_url)
        image = Image.open(BytesIO(response.content))
        hash_value = imagehash.average_hash(image)
        return str(hash_value)

    @staticmethod
    def generate_unique_barcode():
        import uuid
        import time
        
        max_attempts = 10
        for attempt in range(max_attempts):
            timestamp = int(time.time() * 1000)
            random_suffix = str(uuid.uuid4())[:8]
            barcode = f"CARD_{timestamp}_{random_suffix}"
            
            if not Card.objects.filter(barcode=barcode).exists():
                return barcode
        
        raise InternalServerError("Unable to generate unique barcode after multiple attempts")


    @forge
    @require_permission(Permission.CARD_CREATE)
    def post(self, request):
        serializer = CardSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        image = serializer.get_value('image')
        cost_price = serializer.get_value('cost_price')
        base_price = serializer.get_value('base_price')
        max_discount = serializer.get_value('max_discount')
        quantity = serializer.get_value('quantity')
        vendor_id = serializer.get_value('vendor_id')

        barcode = self.generate_unique_barcode()
        perceptual_hash = self.generate_perceptual_hash(image)

        Card.objects.create(image=image, cost_price=cost_price, base_price=base_price, max_discount=max_discount, quantity=quantity, vendor_id=vendor_id, barcode=barcode, perceptual_hash=perceptual_hash)

        return {'message': 'Card created successfully'}


        
