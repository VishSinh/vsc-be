from rest_framework import serializers

from core.constants import NAME_LENGTH, PHONE_LENGTH, PRICE_DECIMAL_PLACES, PRICE_MAX_DIGITS
from core.helpers.base_serializer import BaseSerializer
from core.helpers.param_serializer import ParamSerializer


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


# Parameter Serializers
class CardQueryParams(ParamSerializer):
    """Serializer for card query parameters"""

    card_id = serializers.UUIDField(required=True)


class CardSimilarityParams(ParamSerializer):
    """Serializer for card similarity query parameters"""

    image = serializers.URLField(required=True)


class VendorQueryParams(ParamSerializer):
    """Serializer for vendor query parameters"""

    vendor_id = serializers.UUIDField(required=True)
