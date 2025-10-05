import uuid

from django.db import models

from accounts.models import Staff
from core.constants import (
    CARD_TYPE_LENGTH,
    DEFAULT_AMOUNT,
    DEFAULT_QUANTITY,
    LONG_TEXT_LENGTH,
    NAME_LENGTH,
    PHONE_LENGTH,
    PRICE_DECIMAL_PLACES,
    PRICE_MAX_DIGITS,
    STATUS_LENGTH,
    TAX_DECIMAL_PLACES,
    TAX_MAX_DIGITS,
    TEXT_LENGTH,
)


class Vendor(models.Model):
    """Vendors/suppliers from whom cards are sourced"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=NAME_LENGTH)
    phone = models.CharField(max_length=PHONE_LENGTH)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "vendors"
        verbose_name = "Vendor"
        verbose_name_plural = "Vendors"

    def __str__(self):
        return self.name


class Card(models.Model):
    """Main product catalog with pricing and inventory"""

    class CardType(models.TextChoices):
        SINGLE = "SINGLE", "Single"
        BIRTHDAY = "BIRTHDAY", "Birthday"
        MUNDAN = "MUNDAN", "Mundan"
        CARRY_BAG = "CARRY_BAG", "CarryBag"
        THREE_FOLD = "THREE_FOLD", "ThreeFold"
        FIVE_FOLD = "FIVE_FOLD", "FiveFold"
        ENVELOPE_11X5 = "ENVELOPE_11X5", "Envelope11x5"
        ENVELOPE_9X7 = "ENVELOPE_9X7", "Envelope9x7"
        JUMBO = "JUMBO", "Jumbo"
        BOX = "BOX", "Box"
        PADDING = "PADDING", "Padding"
        URDU_ENVELOPE_11X5 = "URDU_ENVELOPE_11X5", "UrduEnvelope11x5"
        URDU_ENVELOPE_9X7 = "URDU_ENVELOPE_9X7", "UrduEnvelope9x7"
        URDU_CARRY_BAG = "URDU_CARRY_BAG", "UrduCarryBag"
        URDU_JUMBO = "URDU_JUMBO", "UrduJumbo"
        URDU_BOX = "URDU_BOX", "UrduBox"
        URDU_PADDING = "URDU_PADDING", "UrduPadding"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE, related_name="cards")
    barcode = models.CharField(max_length=TEXT_LENGTH, unique=True)
    card_type = models.CharField(max_length=CARD_TYPE_LENGTH, choices=CardType.choices, default=CardType.ENVELOPE_11X5, db_index=True)
    sell_price = models.DecimalField(max_digits=PRICE_MAX_DIGITS, decimal_places=PRICE_DECIMAL_PLACES)
    cost_price = models.DecimalField(max_digits=PRICE_MAX_DIGITS, decimal_places=PRICE_DECIMAL_PLACES)
    max_discount = models.DecimalField(
        max_digits=TAX_MAX_DIGITS,
        decimal_places=TAX_DECIMAL_PLACES,
        default=DEFAULT_AMOUNT,
    )
    quantity = models.IntegerField(default=DEFAULT_QUANTITY)
    image = models.URLField(max_length=LONG_TEXT_LENGTH, blank=True)
    perceptual_hash = models.CharField(max_length=TEXT_LENGTH, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "cards"
        verbose_name = "Card"
        verbose_name_plural = "Cards"

    def __str__(self):
        return f"{self.barcode} - {self.vendor.name}"


class InventoryTransaction(models.Model):
    """Logs all stock movements"""

    class TransactionType(models.TextChoices):
        PURCHASE = "PURCHASE", "Purchase"
        SALE = "SALE", "Sale"
        DAMAGE = "DAMAGE", "Damage"
        RETURN = "RETURN", "Return"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    card = models.ForeignKey(Card, on_delete=models.CASCADE, related_name="inventory_transactions")
    staff = models.ForeignKey(Staff, on_delete=models.CASCADE, related_name="inventory_transactions")
    transaction_type = models.CharField(max_length=STATUS_LENGTH, choices=TransactionType.choices)
    order_item = models.ForeignKey("orders.OrderItem", on_delete=models.CASCADE, related_name="inventory_transactions", null=True, blank=True)
    quantity_changed = models.IntegerField()
    cost_price = models.DecimalField(max_digits=PRICE_MAX_DIGITS, decimal_places=PRICE_DECIMAL_PLACES)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "inventory_transactions"
        verbose_name = "Inventory Transaction"
        verbose_name_plural = "Inventory Transactions"

    def __str__(self):
        return f"{self.transaction_type} - {self.card.barcode} ({self.quantity_changed})"
