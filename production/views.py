from rest_framework.views import APIView

from core.decorators import forge
from core.helpers.pagination import PaginationHelper
from core.utils import model_unwrap
from orders.services import OrderStatusService
from production.models import BoxOrder, PrintingJob
from production.serializers import (
    BoxMakerCreateSerializer,
    BoxMakerQueryParams,
    BoxOrderListParams,
    BoxOrderUpdateSerializer,
    PrinterCreateSerializer,
    PrinterQueryParams,
    PrintingJobUpdateSerializer,
    PrintingListParams,
    TracingListParams,
    TracingStudioCreateSerializer,
    TracingStudioQueryParams,
)
from production.services import BoxMakerService, BoxOrderService, PrinterService, PrintingJobService, TracingStudioService


class BoxOrderView(APIView):
    @forge
    def get(self, request):
        params = BoxOrderListParams.validate_params(request)

        box_maker_id = params.get_value("box_maker_id")
        BoxMakerService.validate_box_maker_exists(box_maker_id)

        queryset = BoxOrderService.get_box_orders_by_box_maker(box_maker_id)

        queryset, page_info = PaginationHelper.paginate_queryset(queryset, params.get_value("page"), params.get_value("page_size"))

        results = [
            {
                "order_name": bo.order_item.order.name,
                "quantity": bo.box_quantity,
                "box_maker_paid": bo.box_maker_paid,
            }
            for bo in queryset
        ]

        return results, page_info

    @forge
    def patch(self, request, box_order_id):
        body = BoxOrderUpdateSerializer.validate_request(request)

        box_order = BoxOrderService.get_box_order_by_id(box_order_id)

        if box_maker_id := body.get_value("box_maker_id"):
            BoxMakerService.validate_box_maker_exists(box_maker_id)

        if box_status := body.get_value("box_status"):
            BoxOrderService.validate_box_status_transition(box_order, box_status)

        if box_type := body.get_value("box_type"):
            BoxOrderService.validate_box_type(box_order, box_type)

        if box_quantity := body.get_value("box_quantity"):
            BoxOrderService.validate_box_quantity(box_order, box_quantity)

        if estimated_completion := body.get_value("estimated_completion"):
            BoxOrderService.validate_estimated_completion(box_order, estimated_completion)

        for field, value in body.validated_data.items():
            if value is not None:
                setattr(box_order, field, value)

        BoxOrderService.update_box_order_status(box_order, box_maker_id=body.get_value("box_maker_id"))

        box_order.save()

        # Update parent order status after change
        parent_order = box_order.order_item.order
        changed = OrderStatusService.mark_in_progress_if_started(parent_order)
        if not changed:
            OrderStatusService.recalculate_ready(parent_order)

        to_return = model_unwrap(box_order)
        to_return["message"] = "Box order updated successfully"
        return to_return


class PrintingJobView(APIView):
    @forge
    def patch(self, request, printing_job_id):
        body = PrintingJobUpdateSerializer.validate_request(request)

        printing_job = PrintingJobService.get_printing_job_by_id(printing_job_id)

        if printer_id := body.get_value("printer_id"):
            PrinterService.validate_printer_exists(printer_id)

        if tracing_studio_id := body.get_value("tracing_studio_id"):
            TracingStudioService.validate_tracing_studio_exists(tracing_studio_id)

        if print_quantity := body.get_value("print_quantity"):
            PrintingJobService.validate_print_quantity(printing_job, print_quantity)

        if printing_status := body.get_value("printing_status"):
            PrintingJobService.validate_printing_status_transition(printing_job, printing_status)

        if estimated_completion := body.get_value("estimated_completion"):
            PrintingJobService.validate_estimated_completion(printing_job, estimated_completion)

        for field, value in body.validated_data.items():
            if value is not None:
                setattr(printing_job, field, value)

        PrintingJobService.update_printing_job_status(
            printing_job, printer_id=body.get_value("printer_id"), tracing_studio_id=body.get_value("tracing_studio_id")
        )
        printing_job.save()

        # Update parent order status after change
        parent_order = printing_job.order_item.order
        changed = OrderStatusService.mark_in_progress_if_started(parent_order)
        if not changed:
            OrderStatusService.recalculate_ready(parent_order)

        to_return = model_unwrap(printing_job)
        to_return["message"] = "Printing job updated successfully"
        return to_return


class PrinterView(APIView):
    @forge
    def get(self, request, printer_id=None):
        if printer_id:
            printer = PrinterService.get_printer_by_id(printer_id)
            return model_unwrap(printer)

        params = PrinterQueryParams.validate_params(request)

        if params.get_value("phone"):
            printer = PrinterService.get_printer_by_phone(params.get_value("phone"))
            return model_unwrap(printer)

        printers = PrinterService.get_printers()
        printers, page_info = PaginationHelper.paginate_queryset(printers, params.get_value("page"), params.get_value("page_size"))
        return [model_unwrap(printer) for printer in printers], page_info

    @forge
    def post(self, request):
        body = PrinterCreateSerializer.validate_request(request)
        PrinterService.create_printer(name=body.get_value("name"), phone=body.get_value("phone"))
        return {"message": "Printer created successfully"}


class TracingStudioView(APIView):
    @forge
    def get(self, request, tracing_studio_id=None):
        if tracing_studio_id:
            tracing_studio = TracingStudioService.get_tracing_studio_by_id(tracing_studio_id)
            return model_unwrap(tracing_studio)

        params = TracingStudioQueryParams.validate_params(request)

        if params.get_value("phone"):
            tracing_studio = TracingStudioService.get_tracing_studio_by_phone(params.get_value("phone"))
            return model_unwrap(tracing_studio)

        tracing_studios = TracingStudioService.get_tracing_studios()
        tracing_studios, page_info = PaginationHelper.paginate_queryset(tracing_studios, params.get_value("page"), params.get_value("page_size"))
        return [model_unwrap(tracing_studio) for tracing_studio in tracing_studios], page_info

    @forge
    def post(self, request):
        body = TracingStudioCreateSerializer.validate_request(request)
        TracingStudioService.create_tracing_studio(name=body.get_value("name"), phone=body.get_value("phone"))
        return {"message": "Tracing studio created successfully"}


class BoxMakerView(APIView):
    @forge
    def get(self, request, box_maker_id=None):
        if box_maker_id:
            box_maker = BoxMakerService.get_box_maker_by_id(box_maker_id)
            return model_unwrap(box_maker)

        params = BoxMakerQueryParams.validate_params(request)

        if params.get_value("phone"):
            box_maker = BoxMakerService.get_box_maker_by_phone(params.get_value("phone"))
            return model_unwrap(box_maker)

        box_makers = BoxMakerService.get_box_makers()
        box_makers, page_info = PaginationHelper.paginate_queryset(box_makers, params.get_value("page"), params.get_value("page_size"))
        return [model_unwrap(box_maker) for box_maker in box_makers], page_info

    @forge
    def post(self, request):
        body = BoxMakerCreateSerializer.validate_request(request)
        BoxMakerService.create_box_maker(name=body.get_value("name"), phone=body.get_value("phone"))
        return {"message": "Box maker created successfully"}


class PrintingView(APIView):

    @forge
    def get(self, request):
        params = PrintingListParams.validate_params(request)

        printer_id = params.get_value("printer_id")
        PrinterService.validate_printer_exists(printer_id)

        queryset = PrintingJobService.get_printing_jobs_by_printer(printer_id)

        queryset, page_info = PaginationHelper.paginate_queryset(queryset, params.get_value("page"), params.get_value("page_size"))

        results = [
            {
                "order_name": pj.order_item.order.name,
                "quantity": pj.print_quantity,
                "printer_paid": pj.printer_paid,
                "impressions": pj.impressions,
            }
            for pj in queryset
        ]

        return results, page_info


class TracingView(APIView):

    @forge
    def get(self, request):
        params = TracingListParams.validate_params(request)

        tracing_studio_id = params.get_value("tracing_studio_id")
        TracingStudioService.validate_tracing_studio_exists(tracing_studio_id)

        queryset = PrintingJobService.get_printing_jobs_by_tracing_studio(tracing_studio_id)

        queryset, page_info = PaginationHelper.paginate_queryset(queryset, params.get_value("page"), params.get_value("page_size"))

        results = [
            {
                "order_name": pj.order_item.order.name,
                "quantity": pj.print_quantity,
                "tracing_studio_paid": pj.tracing_studio_paid,
            }
            for pj in queryset
        ]

        return results, page_info
