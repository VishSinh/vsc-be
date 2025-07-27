import uuid
from django.db import models
from orders.models import OrderItem
from core.constants import (
    PHONE_LENGTH, NAME_LENGTH, STATUS_LENGTH, BOX_TYPE_LENGTH,
    PRICE_MAX_DIGITS, PRICE_DECIMAL_PLACES
)


class Printer(models.Model):
    """Third-party printing service providers"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=NAME_LENGTH)
    phone = models.CharField(max_length=PHONE_LENGTH)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'printers'
        verbose_name = 'Printer'
        verbose_name_plural = 'Printers'

    def __str__(self):
        return self.name


class TracingStudio(models.Model):
    """Third-party tracing service providers"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=NAME_LENGTH)
    phone = models.CharField(max_length=PHONE_LENGTH)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'tracing_studios'
        verbose_name = 'Tracing Studio'
        verbose_name_plural = 'Tracing Studios'

    def __str__(self):
        return self.name


class BoxMaker(models.Model):
    """Third-party box manufacturing providers"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=NAME_LENGTH)
    phone = models.CharField(max_length=PHONE_LENGTH)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'box_makers'
        verbose_name = 'Box Maker'
        verbose_name_plural = 'Box Makers'

    def __str__(self):
        return self.name


class PrintingJob(models.Model):
    """Tracks a specific printing task for an order item"""
    class PrintingStatus(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        IN_PROGRESS = 'IN_PROGRESS', 'In Progress'
        COMPLETED = 'COMPLETED', 'Completed'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order_item = models.ForeignKey(OrderItem, on_delete=models.CASCADE, related_name='printing_jobs')
    printer = models.ForeignKey(Printer, on_delete=models.CASCADE, related_name='printing_jobs')
    tracing_studio = models.ForeignKey(TracingStudio, on_delete=models.CASCADE, related_name='printing_jobs')
    print_quantity = models.IntegerField()
    total_printing_cost = models.DecimalField(max_digits=PRICE_MAX_DIGITS, decimal_places=PRICE_DECIMAL_PLACES)
    printing_status = models.CharField(max_length=STATUS_LENGTH, choices=PrintingStatus.choices, default=PrintingStatus.PENDING)
    estimated_completion = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'printing_jobs'
        verbose_name = 'Printing Job'
        verbose_name_plural = 'Printing Jobs'

    def __str__(self):
        return f"Printing Job {self.id} - {self.order_item.card.barcode}"


class BoxOrder(models.Model):
    """Tracks a specific box creation task for an order item"""
    class BoxStatus(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        IN_PROGRESS = 'IN_PROGRESS', 'In Progress'
        COMPLETED = 'COMPLETED', 'Completed'

    class BoxType(models.TextChoices):
        FOLDING = 'FOLDING', 'Folding'
        COMPLETE = 'COMPLETE', 'Complete'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order_item = models.ForeignKey(OrderItem, on_delete=models.CASCADE, related_name='box_orders')
    box_maker = models.ForeignKey(BoxMaker, on_delete=models.CASCADE, related_name='box_orders')
    box_type = models.CharField(max_length=BOX_TYPE_LENGTH, choices=BoxType.choices)
    box_quantity = models.IntegerField()
    total_box_cost = models.DecimalField(max_digits=PRICE_MAX_DIGITS, decimal_places=PRICE_DECIMAL_PLACES)
    box_status = models.CharField(max_length=STATUS_LENGTH, choices=BoxStatus.choices, default=BoxStatus.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'box_orders'
        verbose_name = 'Box Order'
        verbose_name_plural = 'Box Orders'

    def __str__(self):
        return f"Box Order {self.id} - {self.box_type}"
