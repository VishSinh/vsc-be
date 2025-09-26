import uuid

from django.db import models

from accounts.models import Customer, Staff
from core.constants import (
    DEFAULT_AMOUNT,
    DEFAULT_TAX_PERCENTAGE,
    PAYMENT_MODE_LENGTH,
    PRICE_DECIMAL_PLACES,
    PRICE_MAX_DIGITS,
    SHORT_STATUS_LENGTH,
    STATUS_LENGTH,
    TAX_DECIMAL_PLACES,
    TAX_MAX_DIGITS,
    TEXT_LENGTH,
)
from inventory.models import Card


class Order(models.Model):
    class OrderStatus(models.TextChoices):
        CONFIRMED = "CONFIRMED", "Confirmed"
        IN_PROGRESS = "IN_PROGRESS", "In Progress"
        READY = "READY", "Ready"
        DELIVERED = "DELIVERED", "Delivered"
        FULLY_PAID = "FULLY_PAID", "Fully Paid"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=TEXT_LENGTH)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name="orders")
    staff = models.ForeignKey(Staff, on_delete=models.CASCADE, related_name="orders")
    order_date = models.DateTimeField(auto_now_add=True)
    delivery_date = models.DateTimeField(null=True, blank=True)
    order_status = models.CharField(
        max_length=STATUS_LENGTH,
        choices=OrderStatus.choices,
        default=OrderStatus.CONFIRMED,
    )
    special_instruction = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "orders"
        verbose_name = "Order"
        verbose_name_plural = "Orders"

    def __str__(self):
        return f"Order {self.id} - {self.customer.name}"


class OrderItem(models.Model):
    """A single line item within an order"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="order_items")
    card = models.ForeignKey(Card, on_delete=models.CASCADE, related_name="order_items")
    quantity = models.IntegerField()
    price_per_item = models.DecimalField(max_digits=PRICE_MAX_DIGITS, decimal_places=PRICE_DECIMAL_PLACES)
    discount_amount = models.DecimalField(
        max_digits=PRICE_MAX_DIGITS,
        decimal_places=PRICE_DECIMAL_PLACES,
        default=DEFAULT_AMOUNT,
    )
    requires_box = models.BooleanField(default=False)
    requires_printing = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "order_items"
        verbose_name = "Order Item"
        verbose_name_plural = "Order Items"

    def __str__(self):
        return f"{self.card.barcode} x {self.quantity}"


class Bill(models.Model):
    class PaymentStatus(models.TextChoices):
        PENDING = "PENDING", "Pending"
        PARTIAL = "PARTIAL", "Partial"
        PAID = "PAID", "Paid"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name="bill")
    tax_percentage = models.DecimalField(
        max_digits=TAX_MAX_DIGITS,
        decimal_places=TAX_DECIMAL_PLACES,
        default=DEFAULT_TAX_PERCENTAGE,
    )
    payment_status = models.CharField(
        max_length=SHORT_STATUS_LENGTH,
        choices=PaymentStatus.choices,
        default=PaymentStatus.PENDING,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "bills"
        verbose_name = "Bill"
        verbose_name_plural = "Bills"

    def __str__(self):
        return f"Bill for Order {self.order.id}"


class Payment(models.Model):
    class PaymentMode(models.TextChoices):
        CASH = "CASH", "Cash"
        CARD = "CARD", "Card"
        UPI = "UPI", "UPI"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    bill = models.ForeignKey(Bill, on_delete=models.CASCADE, related_name="payments")
    amount = models.DecimalField(max_digits=PRICE_MAX_DIGITS, decimal_places=PRICE_DECIMAL_PLACES)
    payment_mode = models.CharField(max_length=PAYMENT_MODE_LENGTH, choices=PaymentMode.choices)
    transaction_ref = models.CharField(max_length=TEXT_LENGTH, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "payments"
        verbose_name = "Payment"
        verbose_name_plural = "Payments"

    def __str__(self):
        return f"{self.payment_mode} - {self.amount}"


class BillAdjustment(models.Model):
    class AdjustmentType(models.TextChoices):
        NEGOTIATION = "NEGOTIATION", "Negotiation"
        COMPLAINT = "COMPLAINT", "Complaint"
        GOODWILL = "GOODWILL", "Goodwill"
        OTHER = "OTHER", "Other"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    bill = models.ForeignKey(Bill, on_delete=models.CASCADE, related_name="adjustments")
    staff = models.ForeignKey(Staff, on_delete=models.CASCADE, related_name="bill_adjustments")
    adjustment_type = models.CharField(max_length=STATUS_LENGTH, choices=AdjustmentType.choices)
    amount = models.DecimalField(max_digits=PRICE_MAX_DIGITS, decimal_places=PRICE_DECIMAL_PLACES)
    reason = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "bill_adjustments"
        verbose_name = "Bill Adjustment"
        verbose_name_plural = "Bill Adjustments"

    def __str__(self):
        return f"{self.adjustment_type} - {self.amount}"


class ServiceOrderItem(models.Model):
    class ServiceType(models.TextChoices):
        DIGITAL_CARD = "DIGITAL_CARD", "Digital Card"
        ABHINANDAN_PATR = "ABHINANDAN_PATR", "Abhinandan Patr"
        CAR_POSTER = "CAR_POSTER", "Car Poster"
        DIGITAL_VISITING_CARD = "DIGITAL_VISITING_CARD", "Digital Visiting Card"
        PRINTING_SERVICE = "PRINTING_SERVICE", "Printing Service"
        BOX_SERVICE = "BOX_SERVICE", "Box Service"

    class ProcurementStatus(models.TextChoices):
        REQUESTED = "REQUESTED", "Requested"
        ORDERED = "ORDERED", "Ordered"
        RECEIVED = "RECEIVED", "Received"
        DELIVERED = "DELIVERED", "Delivered"
        CANCELLED = "CANCELLED", "Cancelled"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="service_items")
    service_type = models.CharField(max_length=TEXT_LENGTH, choices=ServiceType.choices)
    quantity = models.PositiveIntegerField()
    procurement_status = models.CharField(max_length=STATUS_LENGTH, choices=ProcurementStatus.choices, default=ProcurementStatus.REQUESTED)
    total_cost = models.DecimalField(max_digits=PRICE_MAX_DIGITS, decimal_places=PRICE_DECIMAL_PLACES)
    total_expense = models.DecimalField(max_digits=PRICE_MAX_DIGITS, decimal_places=PRICE_DECIMAL_PLACES, null=True, blank=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "service_order_items"
        verbose_name = "Service Order Item"
        verbose_name_plural = "Service Order Items"

    def __str__(self):
        return f"{self.service_type} x {self.quantity}"
