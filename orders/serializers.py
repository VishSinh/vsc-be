from rest_framework import serializers

from core.constants import PAGINATION_DEFAULT_PAGE, PAGINATION_DEFAULT_PAGE_SIZE
from core.helpers.base_serializer import BaseSerializer
from core.helpers.param_serializer import ParamSerializer
from production.models import BoxOrder


class OrderQueryParams(ParamSerializer):
    customer_id = serializers.UUIDField(required=False)
    order_date = serializers.DateTimeField(required=False)
    page = serializers.IntegerField(required=False, default=PAGINATION_DEFAULT_PAGE)
    page_size = serializers.IntegerField(required=False, default=PAGINATION_DEFAULT_PAGE_SIZE)


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

    customer_id = serializers.UUIDField(required=True)
    name = serializers.CharField(required=True)
    order_items = serializers.ListField(child=OrderItems(), required=True)
    order_date = serializers.DateTimeField(required=False)
    delivery_date = serializers.DateTimeField(required=True)

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
