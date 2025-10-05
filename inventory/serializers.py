from rest_framework import serializers

from core.constants import NAME_LENGTH, PAGINATION_DEFAULT_PAGE, PAGINATION_DEFAULT_PAGE_SIZE, PHONE_LENGTH, PRICE_DECIMAL_PLACES, PRICE_MAX_DIGITS
from core.helpers.base_serializer import BaseSerializer
from core.helpers.param_serializer import ParamSerializer
from core.helpers.query_params import BaseListParams, build_range_fields
from inventory.models import Card


# ================================================
# Parameter Serializers
# ================================================
class VendorQueryParams(BaseListParams):
    vendor_id = serializers.UUIDField(required=False)


class CardQueryParams(BaseListParams):
    barcode = serializers.CharField(required=False)
    card_type = serializers.ChoiceField(required=False, choices=Card.CardType.choices)
    # Filters
    quantity = serializers.IntegerField(required=False, min_value=0)
    cost_price = serializers.DecimalField(required=False, max_digits=PRICE_MAX_DIGITS, decimal_places=PRICE_DECIMAL_PLACES, min_value=0)

    # Dynamically add range fields via reusable builder
    locals().update(build_range_fields(int_fields=["quantity"], decimal_fields=["cost_price"]))
    # Sorting
    sort_by = serializers.ChoiceField(required=False, choices=["created_at", "cost_price", "quantity"], default="created_at")
    sort_order = serializers.ChoiceField(required=False, choices=["asc", "desc"], default="desc")
    # Pagination comes from BaseListParams


# class CardSimilarityParams(ParamSerializer):
#     image = serializers.URLField(required=True)


# ================================================
# Request Serializers
# ================================================
class VendorSerializer(BaseSerializer):
    name = serializers.CharField(required=True, max_length=NAME_LENGTH)
    phone = serializers.CharField(required=True, max_length=PHONE_LENGTH)


class CardSerializer(BaseSerializer):
    image = serializers.ImageField(required=True)
    card_type = serializers.ChoiceField(required=False, choices=Card.CardType.choices, default=Card.CardType.ENVELOPE_11X5)
    cost_price = serializers.DecimalField(
        required=True,
        max_digits=PRICE_MAX_DIGITS,
        decimal_places=PRICE_DECIMAL_PLACES,
        min_value=0,
    )
    sell_price = serializers.DecimalField(
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


class CardUpdateSerializer(BaseSerializer):
    image = serializers.ImageField(required=False)
    card_type = serializers.ChoiceField(required=False, choices=Card.CardType.choices)
    cost_price = serializers.DecimalField(required=False, max_digits=PRICE_MAX_DIGITS, decimal_places=PRICE_DECIMAL_PLACES, min_value=0)
    sell_price = serializers.DecimalField(required=False, max_digits=PRICE_MAX_DIGITS, decimal_places=PRICE_DECIMAL_PLACES, min_value=0)
    max_discount = serializers.DecimalField(required=False, max_digits=PRICE_MAX_DIGITS, decimal_places=PRICE_DECIMAL_PLACES, min_value=0)
    quantity = serializers.IntegerField(required=False, min_value=0)
    vendor_id = serializers.UUIDField(required=False)


class CardPurchaseSerializer(BaseSerializer):
    quantity = serializers.IntegerField(required=True, min_value=0)


class CardSimilaritySerializer(BaseSerializer):
    image = serializers.ImageField(required=True)
