from typing import Dict, Iterable, Mapping, Optional, Sequence

from rest_framework import serializers

from core.constants import PAGINATION_DEFAULT_PAGE, PAGINATION_DEFAULT_PAGE_SIZE, PRICE_DECIMAL_PLACES, PRICE_MAX_DIGITS
from core.helpers.param_serializer import ParamSerializer


class BaseListParams(ParamSerializer):
    page = serializers.IntegerField(required=False, default=PAGINATION_DEFAULT_PAGE)
    page_size = serializers.IntegerField(required=False, default=PAGINATION_DEFAULT_PAGE_SIZE)

    def validate_page_size(self, value):
        # Cap page size to prevent accidental large queries
        return min(value, 100)


def build_range_fields(
    *,
    int_fields: Iterable[str] = (),
    decimal_fields: Iterable[str] = (),
    lookups: Sequence[str] = ("__gt", "__gte", "__lt", "__lte"),
    field_lookups: Optional[Mapping[str, Sequence[str]]] = None,
) -> Dict[str, serializers.Field]:
    """Return a dict of DRF Fields for numeric range lookups.

    - "lookups" controls the global set of allowed operators.
    - "field_lookups" overrides the allowed operators for specific fields.

    Usage inside a serializer class body:
        locals().update(build_range_fields(
            int_fields=["quantity"],
            decimal_fields=["cost_price"],
            lookups=("__gt", "__lt"),  # exclude __gte/__lte
            field_lookups={"quantity": ("__gt",)},  # per-field overrides
        ))
    """
    fields: Dict[str, serializers.Field] = {}

    def get_lookups_for(field: str) -> Sequence[str]:
        if field_lookups and field in field_lookups:
            return tuple(field_lookups[field])
        return tuple(lookups)

    for field in int_fields:
        for suffix in get_lookups_for(field):
            fields[f"{field}{suffix}"] = serializers.IntegerField(required=False, min_value=0)

    for field in decimal_fields:
        for suffix in get_lookups_for(field):
            fields[f"{field}{suffix}"] = serializers.DecimalField(
                required=False,
                max_digits=PRICE_MAX_DIGITS,
                decimal_places=PRICE_DECIMAL_PLACES,
                min_value=0,
            )

    return fields


def build_date_fields(
    *,
    date_fields: Iterable[str] = (),
    lookups: Sequence[str] = ("__gte", "__lte"),
) -> Dict[str, serializers.Field]:
    """Return a dict of DRF DateField for date range lookups.

    Usage inside a serializer class body:
        locals().update(build_date_fields(date_fields=["order_date"], lookups=("__gte","__lte")))
    """
    fields: Dict[str, serializers.Field] = {}
    for field in date_fields:
        for suffix in tuple(lookups):
            fields[f"{field}{suffix}"] = serializers.DateField(required=False)
    return fields
