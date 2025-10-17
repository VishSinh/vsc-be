from rest_framework import serializers

from core.helpers.base_serializer import BaseSerializer
from core.helpers.query_params import BaseListParams
from production.models import BoxOrder, PrintingJob, VendorPaymentStatus


class PrinterQueryParams(BaseListParams):
    phone = serializers.CharField(required=False)


class TracingStudioQueryParams(BaseListParams):
    phone = serializers.CharField(required=False)


class BoxMakerQueryParams(BaseListParams):
    phone = serializers.CharField(required=False)


class BoxOrderListParams(BaseListParams):
    box_maker_id = serializers.UUIDField(required=True)


class PrintingListParams(BaseListParams):
    printer_id = serializers.UUIDField(required=True)


class TracingListParams(BaseListParams):
    tracing_studio_id = serializers.UUIDField(required=True)


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
    printer_vendor_status = serializers.ChoiceField(required=False, choices=VendorPaymentStatus.choices)
    tracing_vendor_status = serializers.ChoiceField(required=False, choices=VendorPaymentStatus.choices)


class PrinterVendorStatusSerializer(BaseSerializer):
    printer_vendor_status = serializers.ChoiceField(choices=VendorPaymentStatus.choices)


class TracingVendorStatusSerializer(BaseSerializer):
    tracing_vendor_status = serializers.ChoiceField(choices=VendorPaymentStatus.choices)

class BoxingVendorStatusSerializer(BaseSerializer):
    box_maker_vendor_status = serializers.ChoiceField(choices=VendorPaymentStatus.choices)
