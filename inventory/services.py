from django.core.files.uploadedfile import InMemoryUploadedFile
from django.db import transaction

from core.exceptions import Conflict, ResourceNotFound
from core.helpers.image_upload import ImageUpload
from core.helpers.image_utils import ImageUtils
from inventory.models import Card, InventoryTransaction, Vendor


class CardService:
    @staticmethod
    def get_card_by_id(card_id):
        if not (card := Card.objects.filter(id=card_id, is_active=True).first()):
            raise ResourceNotFound("Card not found")

        return card

    @staticmethod
    def get_card_by_barcode(barcode):
        if not (card := Card.objects.filter(barcode=barcode, is_active=True).first()):
            raise ResourceNotFound("Card not found")

        return card

    @staticmethod
    def get_cards():
        return Card.objects.filter(is_active=True).order_by("-created_at")

    @staticmethod
    @transaction.atomic
    def create_card(vendor_id, staff, image_url, cost_price, sell_price, max_discount, quantity, perceptual_hash, card_type=None):
        # 1. Generate unique identifiers
        barcode = ImageUtils.generate_unique_barcode(Card)

        vendor = VendorService.get_vendor_by_id(vendor_id)

        # 2. Create the card instance
        card = Card.objects.create(
            vendor=vendor,
            image=image_url,
            cost_price=cost_price,
            sell_price=sell_price,
            max_discount=max_discount,
            quantity=quantity,
            barcode=barcode,
            perceptual_hash=perceptual_hash,
            card_type=card_type if card_type else Card.CardType.ENVELOPE_11X5,
        )

        # 3. Create the initial inventory transaction to log the purchase
        InventoryTransactionService.record_purchase_transaction(card, quantity, staff)

        return card

    @staticmethod
    def find_similar_cards(image: InMemoryUploadedFile):
        perceptual_hash = ImageUtils.generate_perceptual_hash(image)
        return Card.objects.filter(perceptual_hash=perceptual_hash)

    @staticmethod
    @transaction.atomic  # Ensures the stock update and transaction log are a single operation
    def purchase_additional_stock(card_id, quantity_change, staff):
        # Use select_for_update to lock the row and prevent race conditions
        card = Card.objects.select_for_update().filter(id=card_id).first()
        if not card:
            raise ResourceNotFound("Card not found")

        card.quantity += quantity_change
        card.save()

        InventoryTransactionService.record_purchase_transaction(card, quantity_change, staff)

        return card

    @staticmethod
    def update_card(card_id, **updates):
        card = CardService.get_card_by_id(card_id)

        updatable_fields = {k: v for k, v in updates.items() if v is not None}
        for field, value in updatable_fields.items():
            if field == "image":
                perceptual_hash = ImageUtils.generate_perceptual_hash(value)
                image_url = ImageUpload.upload_image_and_get_url(value)
                card.image = image_url
                card.perceptual_hash = perceptual_hash
                continue
            if field == "vendor_id":
                vendor = VendorService.get_vendor_by_id(value)
                card.vendor = vendor
                continue

            setattr(card, field, value)

        card.save()
        return card

    @staticmethod
    def deactivate_card(card_id):
        card = CardService.get_card_by_id(card_id)
        card.is_active = False
        card.save()
        return card


class InventoryTransactionService:
    @staticmethod
    def record_purchase_transaction(card, quantity, staff):
        InventoryTransaction.objects.create(
            card=card,
            staff=staff,
            transaction_type=InventoryTransaction.TransactionType.PURCHASE,
            quantity_changed=quantity,
            cost_price=card.cost_price,
            notes="Initial stock",
        )

    @staticmethod
    def record_sale_transaction(order_item):
        InventoryTransaction.objects.create(
            card=order_item.card,
            staff=order_item.order.staff,
            transaction_type=InventoryTransaction.TransactionType.SALE,
            order_item=order_item,
            quantity_changed=-order_item.quantity,
            cost_price=order_item.card.cost_price,
            notes="Sale",
        )

    @staticmethod
    def record_return_transaction(order_item):
        InventoryTransaction.objects.create(
            card=order_item.card,
            staff=order_item.order.staff,
            transaction_type=InventoryTransaction.TransactionType.RETURN,
            order_item=order_item,
            quantity_changed=order_item.quantity,
            cost_price=order_item.card.cost_price,
            notes="Return to stock",
        )


class VendorService:
    @staticmethod
    def get_vendor_by_id(vendor_id):
        if not (vendor := Vendor.objects.filter(id=vendor_id).first()):
            raise ResourceNotFound("Vendor not found")

        return vendor

    @staticmethod
    def get_vendors():
        return Vendor.objects.all().order_by("name")

    @staticmethod
    def create_vendor(name, phone):
        if VendorService.check_vendor_exists_by_phone(phone):
            raise Conflict("Vendor with this phone number already exists")

        vendor = Vendor.objects.create(name=name, phone=phone)
        return vendor

    @staticmethod
    def check_vendor_exists_by_phone(phone):
        return Vendor.objects.filter(phone=phone).exists()
