from rest_framework import serializers

from core.constants import NAME_LENGTH, PHONE_LENGTH, PRICE_DECIMAL_PLACES, PRICE_MAX_DIGITS
from core.helpers.base_serializer import BaseSerializer


class VendorSerializer(BaseSerializer):
    name = serializers.CharField(required=True, max_length=NAME_LENGTH)
    phone = serializers.CharField(required=True, max_length=PHONE_LENGTH)


class CardSerializer(BaseSerializer):
    image = serializers.URLField(required=True)
    cost_price = serializers.DecimalField(
        required=True,
        max_digits=PRICE_MAX_DIGITS,
        decimal_places=PRICE_DECIMAL_PLACES,
        min_value=0,
    )
    base_price = serializers.DecimalField(
        required=True,
        max_digits=PRICE_MAX_DIGITS,
        decimal_places=PRICE_DECIMAL_PLACES,
        min_value=0,
    )
    max_discount = serializers.DecimalField(
        required=True,
        max_digits=PRICE_MAX_DIGITS,
        decimal_places=PRICE_DECIMAL_PLACES,
        min_value=0,
    )
    quantity = serializers.IntegerField(required=True, min_value=0)
    vendor_id = serializers.UUIDField(required=True)


class CardPurchaseSerializer(BaseSerializer):
    quantity = serializers.IntegerField(required=True, min_value=0)
