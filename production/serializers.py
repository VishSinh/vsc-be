from rest_framework import serializers

from core.constants import PAGINATION_DEFAULT_PAGE, PAGINATION_DEFAULT_PAGE_SIZE
from core.helpers.base_serializer import BaseSerializer
from core.helpers.param_serializer import ParamSerializer
from production.models import BoxOrder, PrintingJob


class PrinterQueryParams(ParamSerializer):
    phone = serializers.CharField(required=False)
    page = serializers.IntegerField(required=False, default=PAGINATION_DEFAULT_PAGE)
    page_size = serializers.IntegerField(required=False, default=PAGINATION_DEFAULT_PAGE_SIZE)


class TracingStudioQueryParams(ParamSerializer):
    phone = serializers.CharField(required=False)
    page = serializers.IntegerField(required=False, default=PAGINATION_DEFAULT_PAGE)
    page_size = serializers.IntegerField(required=False, default=PAGINATION_DEFAULT_PAGE_SIZE)


class BoxMakerQueryParams(ParamSerializer):
    phone = serializers.CharField(required=False)
    page = serializers.IntegerField(required=False, default=PAGINATION_DEFAULT_PAGE)
    page_size = serializers.IntegerField(required=False, default=PAGINATION_DEFAULT_PAGE_SIZE)


class BoxOrderListParams(ParamSerializer):
    box_maker_id = serializers.UUIDField(required=True)
    page = serializers.IntegerField(required=False, default=PAGINATION_DEFAULT_PAGE)
    page_size = serializers.IntegerField(required=False, default=PAGINATION_DEFAULT_PAGE_SIZE)


class PrintingListParams(ParamSerializer):
    printer_id = serializers.UUIDField(required=True)
    page = serializers.IntegerField(required=False, default=PAGINATION_DEFAULT_PAGE)
    page_size = serializers.IntegerField(required=False, default=PAGINATION_DEFAULT_PAGE_SIZE)


class TracingListParams(ParamSerializer):
    tracing_studio_id = serializers.UUIDField(required=True)
    page = serializers.IntegerField(required=False, default=PAGINATION_DEFAULT_PAGE)
    page_size = serializers.IntegerField(required=False, default=PAGINATION_DEFAULT_PAGE_SIZE)


########################################################


class PrinterCreateSerializer(BaseSerializer):
    name = serializers.CharField(max_length=100)
    phone = serializers.CharField(max_length=15)


class TracingStudioCreateSerializer(BaseSerializer):
    name = serializers.CharField(max_length=100)
    phone = serializers.CharField(max_length=15)


class BoxMakerCreateSerializer(BaseSerializer):
    name = serializers.CharField(max_length=100)
    phone = serializers.CharField(max_length=15)


class BoxOrderUpdateSerializer(BaseSerializer):
    box_maker_id = serializers.UUIDField(required=False)
    total_box_cost = serializers.DecimalField(required=False, max_digits=10, decimal_places=2)
    total_box_expense = serializers.DecimalField(required=False, max_digits=10, decimal_places=2)
    box_status = serializers.ChoiceField(required=False, choices=BoxOrder.BoxStatus.choices)
    box_type = serializers.ChoiceField(required=False, choices=BoxOrder.BoxType.choices)
    box_quantity = serializers.IntegerField(required=False)
    estimated_completion = serializers.DateTimeField(required=False)


class PrintingJobUpdateSerializer(BaseSerializer):
    printer_id = serializers.UUIDField(required=False)
    tracing_studio_id = serializers.UUIDField(required=False)
    impressions = serializers.IntegerField(required=False, min_value=1)
    total_printing_cost = serializers.DecimalField(required=False, max_digits=10, decimal_places=2)
    total_printing_expense = serializers.DecimalField(required=False, max_digits=10, decimal_places=2)
    total_tracing_expense = serializers.DecimalField(required=False, max_digits=10, decimal_places=2)
    printing_status = serializers.ChoiceField(required=False, choices=PrintingJob.PrintingStatus.choices)
    print_quantity = serializers.IntegerField(required=False)
    estimated_completion = serializers.DateTimeField(required=False)
