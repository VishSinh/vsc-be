from django.db import transaction

from core.exceptions import Conflict, ResourceNotFound
from core.helpers.image_utils import ImageUtils
from inventory.models import Card, InventoryTransaction, Vendor


class CardService:
    @staticmethod
    def get_card_by_id(card_id):
        if not (card := Card.objects.filter(id=card_id).first()):
            raise ResourceNotFound("Card not found")

        return card

    @staticmethod
    @transaction.atomic  # Ensures both the Card and its first transaction are created successfully
    def create_card(vendor_id, staff, image, cost_price, base_price, max_discount, quantity):
        """
        Handles the business logic for creating a new card and its initial inventory transaction.
        """
        # 1. Generate unique identifiers
        barcode = ImageUtils.generate_unique_barcode("CARD", Card)
        perceptual_hash = ImageUtils.generate_perceptual_hash(image)

        vendor = VendorService.get_vendor_by_id(vendor_id)

        # 2. Create the card instance
        card = Card.objects.create(
            vendor=vendor,
            image=image,
            cost_price=cost_price,
            base_price=base_price,
            max_discount=max_discount,
            quantity=quantity,
            barcode=barcode,
            perceptual_hash=perceptual_hash,
        )

        # 3. Create the initial inventory transaction to log the purchase
        InventoryTransactionService.record_purchase_transaction(card, quantity, staff)

        return card

    @staticmethod
    def find_similar_cards(image):
        """Finds cards with a matching perceptual hash."""
        perceptual_hash = ImageUtils.generate_perceptual_hash(image)
        return Card.objects.filter(perceptual_hash=perceptual_hash)

    @staticmethod
    @transaction.atomic  # Ensures the stock update and transaction log are a single operation
    def purchase_additional_stock(card_id, quantity_change, staff):
        """
        Purchases additional stock for an existing card and logs the transaction.
        This is used when buying more of an existing card from vendors.
        """
        # Use select_for_update to lock the row and prevent race conditions
        card = Card.objects.select_for_update().filter(id=card_id).first()
        if not card:
            raise ResourceNotFound("Card not found")

        card.quantity += quantity_change
        card.save()

        InventoryTransactionService.record_purchase_transaction(card, quantity_change, staff)

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
    def record_sale_transaction(card, quantity, staff):
        InventoryTransaction.objects.create(
            card=card,
            staff=staff,
            transaction_type=InventoryTransaction.TransactionType.SALE,
            quantity_changed=-quantity,
            cost_price=card.cost_price,
            notes="Sale",
        )


class VendorService:
    @staticmethod
    def get_vendor_by_id(vendor_id):
        if not (vendor := Vendor.objects.filter(id=vendor_id).first()):
            raise ResourceNotFound("Vendor not found")

        return vendor

    @staticmethod
    def create_vendor(name, phone):
        if VendorService.check_vendor_exists_by_phone(phone):
            raise Conflict("Vendor with this phone number already exists")

        vendor = Vendor.objects.create(name=name, phone=phone)
        return vendor

    @staticmethod
    def check_vendor_exists_by_phone(phone):
        return Vendor.objects.filter(phone=phone).exists()
