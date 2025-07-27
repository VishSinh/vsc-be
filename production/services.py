from core.exceptions import Conflict, ResourceNotFound
from production.models import BoxOrder, PrintingJob


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
    def get_box_orders_by_order_item_id(order_item_id):
        if not (box_orders := BoxOrder.objects.filter(order_item=order_item_id)):
            raise ResourceNotFound("Box orders not found")

        return box_orders


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
        if not (printing_jobs := PrintingJob.objects.filter(order_item=order_item_id)):
            raise ResourceNotFound("Printing jobs not found")

        return printing_jobs
