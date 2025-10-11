from rest_framework import serializers

from core.constants import PAGINATION_DEFAULT_PAGE, PAGINATION_DEFAULT_PAGE_SIZE, SERIALIZER_MAX_PHONE_LENGTH, SERIALIZER_MIN_PHONE_LENGTH
from core.helpers.base_serializer import BaseSerializer
from core.helpers.param_serializer import ParamSerializer
from core.helpers.query_params import BaseListParams, build_date_fields
from orders.models import BillAdjustment, Order, Payment, ServiceOrderItem
from production.models import BoxOrder


class OrderQueryParams(BaseListParams):
    customer_id = serializers.UUIDField(required=False)
    phone = serializers.CharField(required=False, min_length=SERIALIZER_MIN_PHONE_LENGTH, max_length=SERIALIZER_MAX_PHONE_LENGTH)

    # Filters
    delivered_or_paid = serializers.BooleanField(required=False)
    order_date = serializers.DateField(required=False)
    # date ranges
    locals().update(build_date_fields(date_fields=["order_date"], lookups=("__gte", "__lte")))

    # Sorting
    sort_by = serializers.ChoiceField(required=False, choices=["order_date"], default="order_date")
    sort_order = serializers.ChoiceField(required=False, choices=["asc", "desc"], default="desc")


class BillQueryParams(BaseListParams):
    order_id = serializers.UUIDField(required=False)
    phone = serializers.CharField(required=False, min_length=SERIALIZER_MIN_PHONE_LENGTH, max_length=SERIALIZER_MAX_PHONE_LENGTH)
    # Filters: paid = True shows only PAID; False shows PENDING or PARTIAL
    paid = serializers.BooleanField(required=False)
    # Sorting
    sort_by = serializers.ChoiceField(required=False, choices=["created_at"], default="created_at")
    sort_order = serializers.ChoiceField(required=False, choices=["asc", "desc"], default="desc")


class PaymentQueryParams(ParamSerializer):
    bill_id = serializers.UUIDField(required=False)
    page = serializers.IntegerField(required=False, default=PAGINATION_DEFAULT_PAGE)
    page_size = serializers.IntegerField(required=False, default=PAGINATION_DEFAULT_PAGE_SIZE)


class BillAdjustmentQueryParams(ParamSerializer):
    bill_id = serializers.UUIDField(required=False)
    page = serializers.IntegerField(required=False, default=PAGINATION_DEFAULT_PAGE)
    page_size = serializers.IntegerField(required=False, default=PAGINATION_DEFAULT_PAGE_SIZE)


#########################


class PaymentCreateSerializer(BaseSerializer):
    bill_id = serializers.UUIDField(required=True)
    amount = serializers.DecimalField(required=True, max_digits=10, decimal_places=2)
    payment_mode = serializers.ChoiceField(choices=Payment.PaymentMode.choices, required=True)
    transaction_ref = serializers.CharField(required=False, allow_blank=True)
    notes = serializers.CharField(required=False, allow_blank=True)


class BillAdjustmentCreateSerializer(BaseSerializer):
    bill_id = serializers.UUIDField(required=True)
    adjustment_type = serializers.ChoiceField(required=True, choices=BillAdjustment.AdjustmentType.choices)
    amount = serializers.DecimalField(required=True, max_digits=10, decimal_places=2)
    reason = serializers.CharField(required=True, allow_blank=False)


class OrderCreateSerializer(BaseSerializer):
    class OrderItems(BaseSerializer):
        card_id = serializers.UUIDField(required=True)
        discount_amount = serializers.DecimalField(required=True, max_digits=10, decimal_places=2)
        quantity = serializers.IntegerField(required=True, min_value=0)
        # Box Order
        requires_box = serializers.BooleanField(required=True)
        box_type = serializers.ChoiceField(choices=BoxOrder.BoxType.choices, required=False, allow_null=True)
        total_box_cost = serializers.DecimalField(max_digits=10, decimal_places=2, required=False, allow_null=True, default=0)
        # Printing Job
        requires_printing = serializers.BooleanField(required=True)
        total_printing_cost = serializers.DecimalField(max_digits=10, decimal_places=2, required=False, allow_null=True, default=0)

    class ServiceItems(BaseSerializer):
        service_type = serializers.ChoiceField(choices=ServiceOrderItem.ServiceType.choices, required=True)
        quantity = serializers.IntegerField(required=True, min_value=1)
        total_cost = serializers.DecimalField(required=True, max_digits=10, decimal_places=2)
        total_expense = serializers.DecimalField(required=True, max_digits=10, decimal_places=2)
        description = serializers.CharField(required=False, allow_blank=True)

    customer_id = serializers.UUIDField(required=True)
    name = serializers.CharField(required=True)
    order_items = serializers.ListField(child=OrderItems(), required=False)
    service_items = serializers.ListField(child=ServiceItems(), required=False)
    order_date = serializers.DateTimeField(required=False)
    delivery_date = serializers.DateTimeField(required=True)

    def validate(self, attrs):
        """Validate that either order_items or service_items (or both) are provided"""
        order_items = attrs.get("order_items")
        service_items = attrs.get("service_items")

        if not order_items and not service_items:
            raise serializers.ValidationError("Either order_items or service_items must be provided")

        return attrs

    def validate_order_items(self, value):
        """Validate that all required fields are provided when production services are requested"""
        for item in value:
            if item.get("requires_box"):
                if item.get("box_type") is None:
                    raise serializers.ValidationError("box_type is required when requires_box is True")
                if item.get("total_box_cost") is None:
                    raise serializers.ValidationError("total_box_cost is required when requires_box is True")

            if item.get("requires_printing"):
                if item.get("total_printing_cost") is None:
                    raise serializers.ValidationError("total_printing_cost is required when requires_printing is True")

        return value


class OrderUpdateSerializer(BaseSerializer):
    class OrderItems(BaseSerializer):
        order_item_id = serializers.UUIDField(required=True)
        quantity = serializers.IntegerField(required=False, min_value=0)
        discount_amount = serializers.DecimalField(required=False, max_digits=10, decimal_places=2)
        requires_box = serializers.BooleanField(required=False)
        box_type = serializers.ChoiceField(required=False, choices=BoxOrder.BoxType.choices)
        total_box_cost = serializers.DecimalField(required=False, max_digits=10, decimal_places=2)
        requires_printing = serializers.BooleanField(required=False)
        total_printing_cost = serializers.DecimalField(required=False, max_digits=10, decimal_places=2)

    order_items = serializers.ListField(child=OrderItems(), required=False)

    class ServiceItemUpdate(BaseSerializer):
        service_order_item_id = serializers.UUIDField(required=True)
        quantity = serializers.IntegerField(required=False, min_value=1)
        procurement_status = serializers.ChoiceField(required=False, choices=ServiceOrderItem.ProcurementStatus.choices)
        total_cost = serializers.DecimalField(required=False, max_digits=10, decimal_places=2)
        total_expense = serializers.DecimalField(required=False, allow_null=True, max_digits=10, decimal_places=2)
        description = serializers.CharField(required=False, allow_blank=True)

    service_items = serializers.ListField(child=ServiceItemUpdate(), required=False)

    class AddOrderItem(BaseSerializer):
        card_id = serializers.UUIDField(required=True)
        discount_amount = serializers.DecimalField(required=True, max_digits=10, decimal_places=2)
        quantity = serializers.IntegerField(required=True, min_value=0)
        requires_box = serializers.BooleanField(required=True)
        box_type = serializers.ChoiceField(choices=BoxOrder.BoxType.choices, required=False, allow_null=True)
        total_box_cost = serializers.DecimalField(max_digits=10, decimal_places=2, required=False, allow_null=True, default=0)
        requires_printing = serializers.BooleanField(required=True)
        total_printing_cost = serializers.DecimalField(max_digits=10, decimal_places=2, required=False, allow_null=True, default=0)

    # Items to add
    add_items = serializers.ListField(child=AddOrderItem(), required=False)
    # Items to remove (by order_item_id)
    remove_item_ids = serializers.ListField(child=serializers.UUIDField(), required=False)
    name = serializers.CharField(required=False, allow_blank=False)
    order_status = serializers.ChoiceField(required=False, choices=Order.OrderStatus.choices)
    delivery_date = serializers.DateTimeField(required=False)
    special_instruction = serializers.CharField(required=False, allow_blank=True)

    class AddServiceItem(BaseSerializer):
        service_type = serializers.ChoiceField(choices=ServiceOrderItem.ServiceType.choices, required=True)
        quantity = serializers.IntegerField(required=True, min_value=1)
        total_cost = serializers.DecimalField(required=True, max_digits=10, decimal_places=2)
        total_expense = serializers.DecimalField(required=False, allow_null=True, max_digits=10, decimal_places=2)
        description = serializers.CharField(required=False, allow_blank=True)

    add_service_items = serializers.ListField(child=AddServiceItem(), required=False)
    remove_service_item_ids = serializers.ListField(child=serializers.UUIDField(), required=False)

    def validate_order_items(self, value):
        for item in value:
            if item.get("requires_box"):
                if item.get("box_type") is None:
                    raise serializers.ValidationError("box_type is required when requires_box is True")
                if item.get("total_box_cost") is None:
                    raise serializers.ValidationError("total_box_cost is required when requires_box is True")

            if item.get("requires_printing"):
                if item.get("total_printing_cost") is None:
                    raise serializers.ValidationError("total_printing_cost is required when requires_printing is True")

        return value

    def validate_add_items(self, value):
        for item in value:
            if item.get("requires_box"):
                if item.get("box_type") is None:
                    raise serializers.ValidationError("box_type is required when requires_box is True")
                if item.get("total_box_cost") is None:
                    raise serializers.ValidationError("total_box_cost is required when requires_box is True")
            if item.get("requires_printing"):
                if item.get("total_printing_cost") is None:
                    raise serializers.ValidationError("total_printing_cost is required when requires_printing is True")
        return value
