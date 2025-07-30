from django.db import transaction
from django.utils import timezone
from rest_framework.views import APIView

from accounts.services import CustomerService
from core.authorization import Permission, require_permission
from core.decorators import forge
from core.exceptions import ResourceNotFound
from core.utils import model_unwrap
from orders.serializers import OrderCreateSerializer
from orders.services import BillService, OrderService
from production.services import BoxOrderService, PrintingJobService


class OrderView(APIView):
    @forge
    def get(self, request, order_id=None):
        def weave(order, order_items):
            order_data = model_unwrap(order)

            order_items_data = []
            for order_item in order_items:
                item_data = model_unwrap(order_item)

                if order_item.requires_box:
                    box_orders = BoxOrderService.get_box_orders_by_order_item_id(order_item.id)
                    item_data["box_orders"] = model_unwrap(box_orders)

                if order_item.requires_printing:
                    printing_jobs = PrintingJobService.get_printing_jobs_by_order_item_id(order_item.id)
                    item_data["printing_jobs"] = model_unwrap(printing_jobs)

                order_items_data.append(item_data)

            return {"order": order_data, "order_items": order_items_data}

        if order_id:
            order = OrderService.get_order_by_id(order_id)
            order_items = OrderService.get_order_items_by_order_id(order_id)
            return weave(order, order_items)

        raise ResourceNotFound("Order ID or appropriate query parameters are required")

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
