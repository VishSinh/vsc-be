from django.db import transaction

from core.helpers.image_utils import ImageUtils
from core.exceptions import ResourceNotFound
from inventory.models import InventoryTransaction, Card, Vendor


class CardService:
    @staticmethod
    @transaction.atomic  # Ensures both the Card and its first transaction are created successfully
    def create_card(vendor_id, staff, image, cost_price, base_price, max_discount, quantity):
        """
        Handles the business logic for creating a new card and its initial inventory transaction.
        """
        # 1. Generate unique identifiers
        barcode = ImageUtils.generate_unique_barcode("CARD", Card)
        perceptual_hash = ImageUtils.generate_perceptual_hash(image)

        vendor = Vendor.objects.get(id=vendor_id)

        # 2. Create the card instance
        card = Card.objects.create(
            vendor=vendor,
            image=image, 
            cost_price=cost_price, 
            base_price=base_price, 
            max_discount=max_discount, 
            quantity=quantity, 
            barcode=barcode, 
            perceptual_hash=perceptual_hash
        )

        # 3. Create the initial inventory transaction to log the purchase
        InventoryTransaction.objects.create(
            card=card, 
            staff=staff, 
            transaction_type=InventoryTransaction.TransactionType.PURCHASE, 
            quantity_changed=quantity, 
            cost_price=cost_price, 
            notes='Initial stock'
        )

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
            raise ResourceNotFound('Card not found')

        # 1. Update the card's quantity
        card.quantity += quantity_change
        card.save()

        # 2. Create the transaction log
        InventoryTransaction.objects.create(
            card=card, 
            staff=staff, 
            transaction_type=InventoryTransaction.TransactionType.PURCHASE,
            quantity_changed=quantity_change, 
            cost_price=card.cost_price,
            notes='Additional stock purchase'
        )
        
        return card


class VendorService:
    @staticmethod
    def create_vendor(name, phone):
        vendor = Vendor.objects.create(name=name, phone=phone)
        return vendor 