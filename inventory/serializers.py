from rest_framework import serializers

from core.constants import NAME_LENGTH, PAGINATION_DEFAULT_PAGE, PAGINATION_DEFAULT_PAGE_SIZE, PHONE_LENGTH, PRICE_DECIMAL_PLACES, PRICE_MAX_DIGITS
from core.helpers.base_serializer import BaseSerializer
from core.helpers.param_serializer import ParamSerializer


# ================================================
# Parameter Serializers
# ================================================
class VendorQueryParams(ParamSerializer):
    vendor_id = serializers.UUIDField(required=False)
    page = serializers.IntegerField(required=False, default=PAGINATION_DEFAULT_PAGE)
    page_size = serializers.IntegerField(required=False, default=PAGINATION_DEFAULT_PAGE_SIZE)


class CardQueryParams(ParamSerializer):
    barcode = serializers.CharField(required=False)
    # Filters
    quantity = serializers.IntegerField(required=False, min_value=0)
    quantity__gt = serializers.IntegerField(required=False, min_value=0)
    quantity__gte = serializers.IntegerField(required=False, min_value=0)
    quantity__lt = serializers.IntegerField(required=False, min_value=0)
    quantity__lte = serializers.IntegerField(required=False, min_value=0)
    cost_price = serializers.DecimalField(
        required=False,
        max_digits=PRICE_MAX_DIGITS,
        decimal_places=PRICE_DECIMAL_PLACES,
        min_value=0,
    )
    cost_price__gt = serializers.DecimalField(
        required=False,
        max_digits=PRICE_MAX_DIGITS,
        decimal_places=PRICE_DECIMAL_PLACES,
        min_value=0,
    )
    cost_price__gte = serializers.DecimalField(
        required=False,
        max_digits=PRICE_MAX_DIGITS,
        decimal_places=PRICE_DECIMAL_PLACES,
        min_value=0,
    )
    cost_price__lt = serializers.DecimalField(
        required=False,
        max_digits=PRICE_MAX_DIGITS,
        decimal_places=PRICE_DECIMAL_PLACES,
        min_value=0,
    )
    cost_price__lte = serializers.DecimalField(
        required=False,
        max_digits=PRICE_MAX_DIGITS,
        decimal_places=PRICE_DECIMAL_PLACES,
        min_value=0,
    )
    # Sorting
    sort_by = serializers.ChoiceField(required=False, choices=["created_at", "cost_price", "quantity"], default="created_at")
    sort_order = serializers.ChoiceField(required=False, choices=["asc", "desc"], default="desc")
    # Pagination
    page = serializers.IntegerField(required=False, default=PAGINATION_DEFAULT_PAGE)
    page_size = serializers.IntegerField(required=False, default=PAGINATION_DEFAULT_PAGE_SIZE)


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
    cost_price = serializers.DecimalField(required=False, max_digits=PRICE_MAX_DIGITS, decimal_places=PRICE_DECIMAL_PLACES, min_value=0)
    sell_price = serializers.DecimalField(required=False, max_digits=PRICE_MAX_DIGITS, decimal_places=PRICE_DECIMAL_PLACES, min_value=0)
    max_discount = serializers.DecimalField(required=False, max_digits=PRICE_MAX_DIGITS, decimal_places=PRICE_DECIMAL_PLACES, min_value=0)
    quantity = serializers.IntegerField(required=False, min_value=0)
    vendor_id = serializers.UUIDField(required=False)


class CardPurchaseSerializer(BaseSerializer):
    quantity = serializers.IntegerField(required=True, min_value=0)


class CardSimilaritySerializer(BaseSerializer):
    image = serializers.ImageField(required=True)
