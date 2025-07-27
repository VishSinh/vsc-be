from rest_framework import serializers

from core.helpers.base_serializer import BaseSerializer
from production.models import BoxOrder


class OrderCreateSerializer(BaseSerializer):
    class OrderItems(BaseSerializer):
        card_id = serializers.UUIDField(required=True)
        discount_amount = serializers.DecimalField(required=True, max_digits=10, decimal_places=2)
        quantity = serializers.IntegerField(required=True, min_value=0)
        # Box Order
        requires_box = serializers.BooleanField(required=True)
        box_type = serializers.ChoiceField(choices=BoxOrder.BoxType.choices, required=False)
        total_box_cost = serializers.DecimalField(max_digits=10, decimal_places=2, required=False)
        # Printing Job
        requires_printing = serializers.BooleanField(required=True)
        total_printing_cost = serializers.DecimalField(max_digits=10, decimal_places=2, required=False)

    customer_id = serializers.UUIDField(required=True)
    order_items = serializers.ListField(child=OrderItems(), required=True)
    order_date = serializers.DateTimeField(required=False)
    delivery_date = serializers.DateTimeField(required=True)

    def validate_order_items(self, value):
        """Validate that all required fields are provided when production services are requested"""
        for item in value:
            if item.get("requires_box"):
                if not item.get("box_type"):
                    raise serializers.ValidationError("box_type is required when requires_box is True")
                if not item.get("total_box_cost"):
                    raise serializers.ValidationError("total_box_cost is required when requires_box is True")

            if item.get("requires_printing"):
                if not item.get("total_printing_cost"):
                    raise serializers.ValidationError("total_printing_cost is required when requires_printing is True")

        return value
