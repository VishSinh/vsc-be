import uuid
from django.db import models
from accounts.models import Staff
from core.constants import (
    PHONE_LENGTH, NAME_LENGTH, TEXT_LENGTH, LONG_TEXT_LENGTH, 
    STATUS_LENGTH, PRICE_MAX_DIGITS, PRICE_DECIMAL_PLACES, 
    TAX_MAX_DIGITS, TAX_DECIMAL_PLACES, DEFAULT_QUANTITY, DEFAULT_AMOUNT
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
        db_table = 'vendors'
        verbose_name = 'Vendor'
        verbose_name_plural = 'Vendors'

    def __str__(self):
        return self.name


class Card(models.Model):
    """Main product catalog with pricing and inventory"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE, related_name='cards')
    barcode = models.CharField(max_length=TEXT_LENGTH, unique=True)
    base_price = models.DecimalField(max_digits=PRICE_MAX_DIGITS, decimal_places=PRICE_DECIMAL_PLACES)
    cost_price = models.DecimalField(max_digits=PRICE_MAX_DIGITS, decimal_places=PRICE_DECIMAL_PLACES)
    max_discount = models.DecimalField(max_digits=TAX_MAX_DIGITS, decimal_places=TAX_DECIMAL_PLACES, default=DEFAULT_AMOUNT)
    quantity = models.IntegerField(default=DEFAULT_QUANTITY)
    image = models.URLField(max_length=LONG_TEXT_LENGTH, blank=True, null=True)
    perceptual_hash = models.CharField(max_length=TEXT_LENGTH, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'cards'
        verbose_name = 'Card'
        verbose_name_plural = 'Cards'

    def __str__(self):
        return f"{self.barcode} - {self.vendor.name}"


class InventoryTransaction(models.Model):
    """Logs all stock movements"""
    class TransactionType(models.TextChoices):
        PURCHASE = 'PURCHASE', 'Purchase'
        SALE = 'SALE', 'Sale'
        DAMAGE = 'DAMAGE', 'Damage'
        RETURN = 'RETURN', 'Return'


    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    card = models.ForeignKey(Card, on_delete=models.CASCADE, related_name='inventory_transactions')
    staff = models.ForeignKey(Staff, on_delete=models.CASCADE, related_name='inventory_transactions')
    transaction_type = models.CharField(max_length=STATUS_LENGTH, choices=TransactionType.choices)
    quantity_changed = models.IntegerField()
    cost_price = models.DecimalField(max_digits=PRICE_MAX_DIGITS, decimal_places=PRICE_DECIMAL_PLACES)
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'inventory_transactions'
        verbose_name = 'Inventory Transaction'
        verbose_name_plural = 'Inventory Transactions'

    def __str__(self):
        return f"{self.transaction_type} - {self.card.barcode} ({self.quantity_changed})"
