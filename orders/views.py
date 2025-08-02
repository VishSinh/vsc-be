from django.db import transaction
from django.utils import timezone
from rest_framework.views import APIView

from accounts.services import CustomerService
from core.authorization import Permission, require_permission
from core.decorators import forge
from core.helpers.pagination import PaginationHelper
from core.utils import model_unwrap
from orders.serializers import OrderCreateSerializer, OrderQueryParams
from orders.services import BillService, OrderService
from production.models import BoxOrder, PrintingJob
from production.services import BoxOrderService, PrintingJobService


class OrderView(APIView):
    @forge
    def get(self, request, order_id=None):
        def weave(order, order_items):
            order_data = model_unwrap(order)

            # Get all order item IDs for bulk queries
            order_item_ids = [item.id for item in order_items]

            # Bulk fetch production data
            box_orders = BoxOrderService.get_box_orders_bulk(order_item_ids)
            printing_jobs = PrintingJobService.get_printing_jobs_bulk(order_item_ids)

            # Create lookup maps for efficient access
            box_orders_map: dict[int, list[BoxOrder]] = {}
            printing_jobs_map: dict[int, list[PrintingJob]] = {}

            for box_order in box_orders:
                if box_order.order_item_id not in box_orders_map:
                    box_orders_map[box_order.order_item_id] = []
                box_orders_map[box_order.order_item_id].append(box_order)

            for printing_job in printing_jobs:
                if printing_job.order_item_id not in printing_jobs_map:
                    printing_jobs_map[printing_job.order_item_id] = []
                printing_jobs_map[printing_job.order_item_id].append(printing_job)

            order_items_data = []
            for order_item in order_items:
                item_data = model_unwrap(order_item)

                if order_item.requires_box:
                    item_data["box_orders"] = model_unwrap(box_orders_map.get(order_item.id, []))

                if order_item.requires_printing:
                    item_data["printing_jobs"] = model_unwrap(printing_jobs_map.get(order_item.id, []))

                order_items_data.append(item_data)

            order_data["order_items"] = order_items_data

            return order_data

        #########################################################
        #########################################################
        #########################################################

        if order_id:
            order, order_items = OrderService.get_order_with_items(order_id)
            return weave(order, order_items)

        #########################################################

        params = OrderQueryParams.validate_params(request)

        if params.get_value("customer_id"):
            orders_queryset = OrderService.get_orders_by_customer_id(params.get_value("customer_id"))
        elif params.get_value("order_date"):
            orders_queryset = OrderService.get_orders_by_order_date(params.get_value("order_date"))
        else:
            orders_queryset = OrderService.get_orders()

        orders, page_info = PaginationHelper.paginate_queryset(orders_queryset, params.get_value("page"), params.get_value("page_size"))

        orders_with_items = OrderService.get_orders_with_items_bulk(orders)

        weaved_orders = []
        for order_data in orders_with_items:
            weaved_orders.append(weave(order_data["order"], order_data["order_items"]))

        return weaved_orders, page_info

    @forge
    @require_permission(Permission.ORDER_CREATE)
    @transaction.atomic
    def post(self, request):
        body = OrderCreateSerializer.validate_request(request)

        print("body", body)

        staff = request.staff
        customer = CustomerService.get_customer_by_id(body.get_value("customer_id"))
        order_date = body.get_value("order_date", timezone.now())
        delivery_date = body.get_value("delivery_date")
        order_items = body.get_value("order_items")
        special_instruction = body.get_value("special_instruction", "")

        # Create Order
        order = OrderService.create_order(customer, staff, order_date, delivery_date, special_instruction)

        # Create Order Items and Production Services
        for item in order_items:
            order_item = OrderService.create_order_item(
                order=order,
                card_id=item.get("card_id"),
                discount_amount=item.get("discount_amount", 0),
                quantity=item.get("quantity"),
                requires_box=item.get("requires_box"),
                requires_printing=item.get("requires_printing"),
            )

            if item.get("requires_box"):
                box_order = BoxOrderService.create_box_order(
                    order_item=order_item,
                    box_type=item.get("box_type"),
                    quantity=item.get("quantity"),
                    total_box_cost=item.get("total_box_cost"),
                )
                print("Created Box Order \n", box_order)

            if item.get("requires_printing"):
                printing_job = PrintingJobService.create_printing_job(
                    order_item=order_item,
                    quantity=item.get("quantity"),
                    total_printing_cost=item.get("total_printing_cost"),
                )
                print("Created Printing Job \n", printing_job)

        # Create Bill
        BillService.create_bill(order)

        return {"message": "Order created successfully"}
