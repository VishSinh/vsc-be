from core.exceptions import Conflict, ResourceNotFound
from django.db.models import Case, IntegerField, Value, When
from orders.services import OrderStatusService
from production.models import BoxMaker, BoxOrder, Printer, PrintingJob, TracingStudio, VendorPaymentStatus


class BoxOrderService:
    @staticmethod
    def create_box_order(order_item, box_type, quantity, total_box_cost):
        box_orders = BoxOrder.objects.filter(order_item=order_item)

        total_quantity = 0
        if box_orders.exists():
            for box_order in box_orders:
                total_quantity += box_order.box_quantity

        if total_quantity + quantity > order_item.quantity:
            raise Conflict("Quantity is greater than order item quantity")

        # Create box order
        box_order = BoxOrder.objects.create(
            order_item=order_item,
            box_type=box_type,
            box_quantity=quantity,
            total_box_cost=total_box_cost,
        )

        return box_order

    @staticmethod
    def get_box_order_by_id(box_order_id):
        if not (box_order := BoxOrder.objects.filter(id=box_order_id).first()):
            raise ResourceNotFound("Box order not found")

        return box_order

    @staticmethod
    def get_box_orders_by_order_item_id(order_item_id):
        return BoxOrder.objects.filter(order_item=order_item_id)

    @staticmethod
    def get_box_orders_bulk(order_item_ids):
        """Get box orders for multiple order items in one query"""
        return BoxOrder.objects.filter(order_item_id__in=order_item_ids)

    @staticmethod
    def get_box_orders_by_box_maker(box_maker_id):
        """Get box orders for a specific box maker with necessary relations"""
        # Order by vendor payment status: PENDING -> DELIVERED -> PAID, then newest first
        status_order = Case(
            When(box_maker_vendor_status=VendorPaymentStatus.PENDING, then=Value(0)),
            When(box_maker_vendor_status=VendorPaymentStatus.DELIVERED, then=Value(1)),
            When(box_maker_vendor_status=VendorPaymentStatus.PAID, then=Value(2)),
            default=Value(3),
            output_field=IntegerField(),
        )
        return (
            BoxOrder.objects.filter(box_maker_id=box_maker_id)
            .select_related("order_item", "order_item__order")
            .order_by(status_order, "-created_at")
        )

    @staticmethod
    def get_latest_by_order_item_id(order_item_id):
        return BoxOrder.objects.filter(order_item_id=order_item_id).order_by("-created_at").first()

    @staticmethod
    def delete_by_order_item(order_item):
        BoxOrder.objects.filter(order_item=order_item).delete()

    @staticmethod
    def update_box_order(
        box_order,
        box_type=None,
        box_quantity=None,
        total_box_cost=None,
        box_status=None,
        box_maker_id=None,
        estimated_completion=None,
        box_maker_vendor_status=None,
    ):
        if box_type is not None:
            BoxOrderService.validate_box_type(box_order, box_type)
            box_order.box_type = box_type
        if box_quantity is not None:
            BoxOrderService.validate_box_quantity(box_order, box_quantity)
            box_order.box_quantity = box_quantity
        if total_box_cost is not None:
            box_order.total_box_cost = total_box_cost
        if estimated_completion is not None:
            BoxOrderService.validate_estimated_completion(box_order, estimated_completion)
            box_order.estimated_completion = estimated_completion
        if box_status is not None:
            BoxOrderService.validate_box_status_transition(box_order, box_status)
            box_order.box_status = box_status
        if box_maker_vendor_status is not None:
            box_order.box_maker_vendor_status = box_maker_vendor_status
        if box_maker_id is not None:
            from production.services import BoxMakerService

            box_order.box_maker = BoxMakerService.validate_box_maker_exists(box_maker_id)
        # If vendor status is PAID, ensure completed
        if getattr(box_order, "box_maker_vendor_status", VendorPaymentStatus.PENDING) == VendorPaymentStatus.PAID and box_order.box_status != BoxOrder.BoxStatus.COMPLETED:
            box_order.box_status = BoxOrder.BoxStatus.COMPLETED
        BoxOrderService.update_box_order_status(box_order, box_maker_id=box_maker_id)
        box_order.save()

        # Update parent order status (IN_PROGRESS/READY recalculation)
        parent_order = box_order.order_item.order
        changed = OrderStatusService.mark_in_progress_if_started(parent_order)
        if not changed:
            OrderStatusService.recalculate_ready(parent_order)
        return box_order

    @staticmethod
    def validate_box_quantity(box_order, new_quantity):
        """Validate that total box quantity doesn't exceed order item quantity"""
        if new_quantity is None:
            return

        # Get all box orders for this order item (excluding current one if updating)
        other_box_orders = BoxOrder.objects.filter(order_item=box_order.order_item).exclude(id=box_order.id)

        # Calculate total quantity from other box orders
        total_other_quantity = sum(box.box_quantity for box in other_box_orders)

        # Check if new total would exceed order item quantity
        if total_other_quantity + new_quantity > box_order.order_item.quantity:
            raise Conflict(
                f"Total box quantity ({total_other_quantity + new_quantity}) would exceed order item quantity ({box_order.order_item.quantity})"
            )

    @staticmethod
    def validate_box_status_transition(box_order, new_status, raise_error=True):
        """Validate box status transition follows proper workflow"""
        if new_status is None:
            return True

        valid_transitions = {
            BoxOrder.BoxStatus.PENDING: [BoxOrder.BoxStatus.IN_PROGRESS, BoxOrder.BoxStatus.COMPLETED],
            BoxOrder.BoxStatus.IN_PROGRESS: [BoxOrder.BoxStatus.COMPLETED],
            BoxOrder.BoxStatus.COMPLETED: [],  # No further transitions allowed
        }

        current_status = box_order.box_status
        valid_transitions_for_status = valid_transitions.get(current_status, [])
        is_valid = new_status in valid_transitions_for_status  # type: ignore

        if not is_valid and raise_error:
            raise Conflict(f"Invalid status transition from {current_status} to {new_status}.")
        return is_valid

    @staticmethod
    def validate_estimated_completion(box_order, estimated_completion):
        """Validate estimated completion date is valid"""
        if estimated_completion is None:
            return

        from django.utils import timezone

        # Check if estimated completion is in the past
        if estimated_completion < timezone.now():
            raise Conflict("Estimated completion cannot be in the past")

        # Check if estimated completion is before order delivery date
        order_delivery_date = box_order.order_item.order.delivery_date
        if order_delivery_date and estimated_completion > order_delivery_date:
            raise Conflict("Estimated completion cannot be after order delivery date")

    @staticmethod
    def update_box_order_status(box_order, box_maker_id=None):
        """Update box order status based on provider assignment"""
        status_changed = False

        # If box maker is assigned and status is not IN_PROGRESS, transition to IN_PROGRESS
        if box_maker_id and box_order.box_status != BoxOrder.BoxStatus.IN_PROGRESS:
            if BoxOrderService.validate_box_status_transition(box_order, BoxOrder.BoxStatus.IN_PROGRESS, raise_error=False):
                box_order.box_status = BoxOrder.BoxStatus.IN_PROGRESS
                status_changed = True

        # If vendor status is PAID, mark as COMPLETED when allowed
        if getattr(box_order, "box_maker_vendor_status", None) == VendorPaymentStatus.PAID and box_order.box_status != BoxOrder.BoxStatus.COMPLETED:
            if BoxOrderService.validate_box_status_transition(box_order, BoxOrder.BoxStatus.COMPLETED, raise_error=False):
                box_order.box_status = BoxOrder.BoxStatus.COMPLETED
                status_changed = True

        return status_changed

    @staticmethod
    def set_box_maker_vendor_status(box_order_id, vendor_status):
        box_order = BoxOrderService.get_box_order_by_id(box_order_id)
        box_order.box_maker_vendor_status = vendor_status
        # If PAID, optionally move to COMPLETED
        if vendor_status == VendorPaymentStatus.PAID and box_order.box_status != BoxOrder.BoxStatus.COMPLETED:
            box_order.box_status = BoxOrder.BoxStatus.COMPLETED
        box_order.save(update_fields=["box_maker_vendor_status", "updated_at"])
        return box_order

    @staticmethod
    def validate_box_type(box_order, new_box_type):
        """Validate box type is valid"""
        if new_box_type is None:
            return

        valid_types = [choice[0] for choice in BoxOrder.BoxType.choices]
        if new_box_type not in valid_types:
            raise Conflict(f"Invalid box type: {new_box_type}. Valid types: {valid_types}")


class PrintingJobService:
    @staticmethod
    def create_printing_job(order_item, quantity, total_printing_cost):
        printing_jobs = PrintingJob.objects.filter(order_item=order_item)

        total_quantity = 0
        if printing_jobs.exists():
            for printing_job in printing_jobs:
                total_quantity += printing_job.print_quantity

        if total_quantity + quantity > order_item.quantity:
            raise Conflict("Quantity is greater than order item quantity")

        printing_job = PrintingJob.objects.create(
            order_item=order_item,
            print_quantity=quantity,
            total_printing_cost=total_printing_cost,
        )

        return printing_job

    @staticmethod
    def get_printing_jobs_by_order_item_id(order_item_id):
        return PrintingJob.objects.filter(order_item=order_item_id)

    @staticmethod
    def get_printing_jobs_bulk(order_item_ids):
        """Get printing jobs for multiple order items in one query"""
        return PrintingJob.objects.filter(order_item_id__in=order_item_ids)

    @staticmethod
    def get_printing_jobs_by_printer(printer_id):
        """Get printing jobs assigned to a specific printer with necessary relations"""
        # Order by printer vendor payment status: PENDING -> DELIVERED -> PAID, then newest first
        status_order = Case(
            When(printer_vendor_status=VendorPaymentStatus.PENDING, then=Value(0)),
            When(printer_vendor_status=VendorPaymentStatus.DELIVERED, then=Value(1)),
            When(printer_vendor_status=VendorPaymentStatus.PAID, then=Value(2)),
            default=Value(3),
            output_field=IntegerField(),
        )
        return (
            PrintingJob.objects.filter(printer_id=printer_id)
            .select_related("order_item", "order_item__order")
            .order_by(status_order, "-created_at")
        )

    @staticmethod
    def get_printing_jobs_by_tracing_studio(tracing_studio_id):
        """Get printing jobs assigned to a specific tracing studio with necessary relations"""
        # Order by tracing vendor payment status: PENDING -> DELIVERED -> PAID, then newest first
        status_order = Case(
            When(tracing_vendor_status=VendorPaymentStatus.PENDING, then=Value(0)),
            When(tracing_vendor_status=VendorPaymentStatus.DELIVERED, then=Value(1)),
            When(tracing_vendor_status=VendorPaymentStatus.PAID, then=Value(2)),
            default=Value(3),
            output_field=IntegerField(),
        )
        return (
            PrintingJob.objects.filter(tracing_studio_id=tracing_studio_id)
            .select_related("order_item", "order_item__order")
            .order_by(status_order, "-created_at")
        )

    @staticmethod
    def get_latest_by_order_item_id(order_item_id):
        return PrintingJob.objects.filter(order_item_id=order_item_id).order_by("-created_at").first()

    @staticmethod
    def delete_by_order_item(order_item):
        PrintingJob.objects.filter(order_item=order_item).delete()

    @staticmethod
    def update_printing_job(
        printing_job,
        total_printing_cost=None,
        print_quantity=None,
        printing_status=None,
        printer_id=None,
        tracing_studio_id=None,
        estimated_completion=None,
    ):
        if print_quantity is not None:
            PrintingJobService.validate_print_quantity(printing_job, print_quantity)
            printing_job.print_quantity = print_quantity
        if total_printing_cost is not None:
            printing_job.total_printing_cost = total_printing_cost
        if estimated_completion is not None:
            PrintingJobService.validate_estimated_completion(printing_job, estimated_completion)
            printing_job.estimated_completion = estimated_completion
        if printing_status is not None:
            PrintingJobService.validate_printing_status_transition(printing_job, printing_status)
            printing_job.printing_status = printing_status
        if printer_id is not None:
            from production.services import PrinterService

            printing_job.printer = PrinterService.validate_printer_exists(printer_id)
        if tracing_studio_id is not None:
            from production.services import TracingStudioService

            printing_job.tracing_studio = TracingStudioService.validate_tracing_studio_exists(tracing_studio_id)
        PrintingJobService.update_printing_job_status(printing_job, printer_id=printer_id, tracing_studio_id=tracing_studio_id)
        printing_job.save()

        # Update parent order status (IN_PROGRESS/READY recalculation)
        parent_order = printing_job.order_item.order
        changed = OrderStatusService.mark_in_progress_if_started(parent_order)
        if not changed:
            OrderStatusService.recalculate_ready(parent_order)
        return printing_job

    @staticmethod
    def get_printing_job_by_id(printing_job_id):
        if not (printing_job := PrintingJob.objects.filter(id=printing_job_id).first()):
            raise ResourceNotFound("Printing job not found")

        return printing_job

    @staticmethod
    def set_printer_vendor_status(printing_job_id, vendor_status):
        printing_job = PrintingJobService.get_printing_job_by_id(printing_job_id)
        printing_job.printer_vendor_status = vendor_status
        if vendor_status == VendorPaymentStatus.PAID and printing_job.printing_status != PrintingJob.PrintingStatus.COMPLETED:
            printing_job.printing_status = PrintingJob.PrintingStatus.COMPLETED
        printing_job.save(update_fields=["printer_vendor_status", "updated_at"])
        return printing_job

    @staticmethod
    def set_tracing_vendor_status(printing_job_id, vendor_status):
        printing_job = PrintingJobService.get_printing_job_by_id(printing_job_id)
        printing_job.tracing_vendor_status = vendor_status
        printing_job.save(update_fields=["tracing_vendor_status", "updated_at"])
        return printing_job

    @staticmethod
    def validate_print_quantity(printing_job, new_quantity):
        """Validate that total print quantity doesn't exceed order item quantity"""
        if new_quantity is None:
            return

        # Get all printing jobs for this order item (excluding current one if updating)
        other_printing_jobs = PrintingJob.objects.filter(order_item=printing_job.order_item).exclude(id=printing_job.id)

        # Calculate total quantity from other printing jobs
        total_other_quantity = sum(job.print_quantity for job in other_printing_jobs)

        # Check if new total would exceed order item quantity
        if total_other_quantity + new_quantity > printing_job.order_item.quantity:
            raise Conflict(
                f"Total print quantity ({total_other_quantity + new_quantity}) would exceed order item quantity ({printing_job.order_item.quantity})"
            )

    @staticmethod
    def validate_printing_status_transition(printing_job, new_status, raise_error=True):
        """Validate printing status transition follows proper workflow"""
        if new_status is None:
            return

        valid_transitions = {
            PrintingJob.PrintingStatus.PENDING: [
                PrintingJob.PrintingStatus.IN_TRACING,
                PrintingJob.PrintingStatus.IN_PRINTING,
                PrintingJob.PrintingStatus.COMPLETED,
            ],
            PrintingJob.PrintingStatus.IN_TRACING: [PrintingJob.PrintingStatus.IN_PRINTING, PrintingJob.PrintingStatus.COMPLETED],
            PrintingJob.PrintingStatus.IN_PRINTING: [PrintingJob.PrintingStatus.COMPLETED],
            PrintingJob.PrintingStatus.COMPLETED: [],  # No further transitions allowed
        }

        current_status = printing_job.printing_status
        valid_transitions_for_status = valid_transitions.get(current_status, [])
        is_valid = new_status in valid_transitions_for_status  # type: ignore

        if not is_valid and raise_error:
            raise Conflict(f"Invalid status transition from {current_status} to {new_status}.")

        return is_valid

    @staticmethod
    def update_printing_job_status(printing_job, printer_id=None, tracing_studio_id=None):
        """Update printing job status based on provider assignments"""
        status_changed = False

        # If tracing studio is assigned and status is not IN_TRACING, transition to IN_TRACING
        if tracing_studio_id and printing_job.printing_status != PrintingJob.PrintingStatus.IN_TRACING:
            if PrintingJobService.validate_printing_status_transition(printing_job, PrintingJob.PrintingStatus.IN_TRACING, raise_error=False):
                printing_job.printing_status = PrintingJob.PrintingStatus.IN_TRACING
                status_changed = True

        # If printer is assigned and status is not IN_PRINTING, transition to IN_PRINTING
        if printer_id and printing_job.printing_status != PrintingJob.PrintingStatus.IN_PRINTING:
            if PrintingJobService.validate_printing_status_transition(printing_job, PrintingJob.PrintingStatus.IN_PRINTING, raise_error=False):
                printing_job.printing_status = PrintingJob.PrintingStatus.IN_PRINTING
                status_changed = True

        return status_changed

    @staticmethod
    def validate_estimated_completion(printing_job, estimated_completion):
        """Validate estimated completion date is valid"""
        if estimated_completion is None:
            return

        from django.utils import timezone

        # Check if estimated completion is in the past
        if estimated_completion < timezone.now():
            raise Conflict("Estimated completion cannot be in the past")

        # Check if estimated completion is before order delivery date
        order_delivery_date = printing_job.order_item.order.delivery_date
        if order_delivery_date and estimated_completion > order_delivery_date:
            raise Conflict("Estimated completion cannot be after order delivery date")


class PrinterService:
    @staticmethod
    def get_printer_by_id(printer_id):
        if not (printer := Printer.objects.filter(id=printer_id, is_active=True).first()):
            raise ResourceNotFound("Printer not found")
        return printer

    @staticmethod
    def get_printer_by_phone(phone):
        return Printer.objects.filter(phone=phone, is_active=True).first()

    @staticmethod
    def get_printers():
        return Printer.objects.filter(is_active=True).order_by("name")

    @staticmethod
    def create_printer(name, phone):
        if Printer.objects.filter(phone=phone, is_active=True).exists():
            raise Conflict("Printer with this phone number already exists")
        return Printer.objects.create(name=name, phone=phone)

    @staticmethod
    def validate_printer_exists(printer_id):
        """Validate that the printer exists and is active"""
        if not (printer := Printer.objects.filter(id=printer_id, is_active=True).first()):
            raise ResourceNotFound("Printer not found or inactive")
        return printer


class TracingStudioService:
    @staticmethod
    def get_tracing_studio_by_id(tracing_studio_id):
        if not (tracing_studio := TracingStudio.objects.filter(id=tracing_studio_id, is_active=True).first()):
            raise ResourceNotFound("Tracing studio not found")
        return tracing_studio

    @staticmethod
    def get_tracing_studio_by_phone(phone):
        return TracingStudio.objects.filter(phone=phone, is_active=True).first()

    @staticmethod
    def get_tracing_studios():
        return TracingStudio.objects.filter(is_active=True).order_by("name")

    @staticmethod
    def create_tracing_studio(name, phone):
        if TracingStudio.objects.filter(phone=phone, is_active=True).exists():
            raise Conflict("Tracing studio with this phone number already exists")
        return TracingStudio.objects.create(name=name, phone=phone)

    @staticmethod
    def validate_tracing_studio_exists(tracing_studio_id):
        """Validate that the tracing studio exists and is active"""
        if not (tracing_studio := TracingStudio.objects.filter(id=tracing_studio_id, is_active=True).first()):
            raise ResourceNotFound("Tracing studio not found or inactive")
        return tracing_studio


class BoxMakerService:
    @staticmethod
    def get_box_maker_by_id(box_maker_id):
        if not (box_maker := BoxMaker.objects.filter(id=box_maker_id, is_active=True).first()):
            raise ResourceNotFound("Box maker not found")
        return box_maker

    @staticmethod
    def get_box_maker_by_phone(phone):
        return BoxMaker.objects.filter(phone=phone, is_active=True).first()

    @staticmethod
    def get_box_makers():
        return BoxMaker.objects.filter(is_active=True).order_by("name")

    @staticmethod
    def create_box_maker(name, phone):
        if BoxMaker.objects.filter(phone=phone, is_active=True).exists():
            raise Conflict("Box maker with this phone number already exists")
        return BoxMaker.objects.create(name=name, phone=phone)

    @staticmethod
    def validate_box_maker_exists(box_maker_id):
        """Validate that the box maker exists and is active"""
        if not (box_maker := BoxMaker.objects.filter(id=box_maker_id, is_active=True).first()):
            raise ResourceNotFound("Box maker not found or inactive")
        return box_maker
