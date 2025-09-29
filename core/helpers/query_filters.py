from typing import Iterable, Mapping, Sequence, Union, Optional, Dict, Callable


class QueryFilterSortHelper:
    """Generic helper to apply filters and sorting to a queryset.

    Usage pattern:
        helper = QueryFilterSortHelper(
            allowed_filter_fields=["quantity", "cost_price"],
            allowed_sort_fields=["created_at", "cost_price", "quantity"],
            default_sort_by="created_at",
            default_sort_order="desc",
        )
        qs = helper.apply(qs, params_serializer)

    - Filters: supports exact and range lookups for allowed fields
      Supported lookups per field: "", "__gt", "__gte", "__lt", "__lte"
      Example params: quantity=10, quantity__gt=0, cost_price__lte=100

    - Sorting: expects params "sort_by" and "sort_order" ("asc" | "desc")
    """

    SUPPORTED_LOOKUPS: Sequence[str] = ("", "__gt", "__gte", "__lt", "__lte")

    def __init__(
        self,
        *,
        allowed_filter_fields: Sequence[str],
        allowed_sort_fields: Sequence[str],
        default_sort_by: str,
        default_sort_order: str = "desc",
        per_field_lookups: Optional[Dict[str, Sequence[str]]] = None,
        field_transform: Optional[Callable[[str], str]] = None,
    ) -> None:
        self.allowed_filter_fields = tuple(allowed_filter_fields)
        self.allowed_sort_fields = tuple(allowed_sort_fields)
        self.default_sort_by = default_sort_by
        self.default_sort_order = default_sort_order
        self.per_field_lookups = per_field_lookups or {}
        self.field_transform = field_transform

    def apply(self, queryset, params: Union[Mapping, object]):
        values = self._extract_values(params)

        # Build filter kwargs
        filter_kwargs = {}
        for field in self.allowed_filter_fields:
            allowed_lookups = self.per_field_lookups.get(field, self.SUPPORTED_LOOKUPS)
            for lookup in allowed_lookups:
                param_name = f"{field}{lookup}"
                if param_name in values:
                    value = values.get(param_name)
                    if value is not None and value != "":
                        target_field = field
                        if self.field_transform:
                            target_field = self.field_transform(field)
                        filter_key = f"{target_field}{lookup}"
                        filter_kwargs[filter_key] = value

        if filter_kwargs:
            queryset = queryset.filter(**filter_kwargs)

        # Sorting
        sort_by = values.get("sort_by", self.default_sort_by)
        sort_order = values.get("sort_order", self.default_sort_order)

        if sort_by not in self.allowed_sort_fields:
            sort_by = self.default_sort_by
        if sort_order not in ("asc", "desc"):
            sort_order = self.default_sort_order

        target_sort_field = sort_by
        if self.field_transform:
            target_sort_field = self.field_transform(sort_by)
        order_field = f"-{target_sort_field}" if sort_order == "desc" else target_sort_field
        queryset = queryset.order_by(order_field)

        return queryset

    @staticmethod
    def _extract_values(params: Union[Mapping, object]) -> Mapping:
        if hasattr(params, "validated_data") and isinstance(getattr(params, "validated_data"), dict):
            return params.validated_data  # ParamSerializer instance
        if isinstance(params, dict):
            return params
        # Fallback: try to access as mapping-like
        return getattr(params, "__dict__", {})


