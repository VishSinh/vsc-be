from decimal import Decimal

from django.db import models, transaction
from django.utils import timezone
from rest_framework.views import APIView

from accounts.services import CustomerService
from core.authorization import Permission, require_permission
from core.decorators import forge
from core.helpers.pagination import PaginationHelper
from core.utils import model_unwrap
from orders.serializers import (
    BillQueryParams,
    OrderCreateSerializer,
    OrderQueryParams,
    OrderUpdateSerializer,
    PaymentCreateSerializer,
    PaymentQueryParams,
)
from orders.services import BillService, OrderService, PaymentService, ServiceOrderItemService
from production.services import BoxOrderService, PrintingJobService


class OrderView(APIView):
    @forge
    def get(self, request, order_id=None):
        def weave(order):
            order_data = model_unwrap(order)
            order_items_data = []
            for order_item in order.order_items.all():
                item_data = model_unwrap(order_item)
                if order_item.requires_box:
                    item_data["box_orders"] = model_unwrap(order_item.box_orders.all())
                if order_item.requires_printing:
                    item_data["printing_jobs"] = model_unwrap(order_item.printing_jobs.all())
                order_items_data.append(item_data)
            order_data["order_items"] = order_items_data
            order_data["service_items"] = model_unwrap(order.service_items.all())
            order_data["bill_id"] = model_unwrap(order.bill).get("id")
            return order_data

        if order_id:
            order = OrderService.get_order_by_id(order_id)
            return weave(order)

        params = OrderQueryParams.validate_params(request)

        orders_queryset = OrderService.get_orders(
            customer_id=params.get_value("customer_id"),
            order_date=params.get_value("order_date"),
        )

        orders, page_info = PaginationHelper.paginate_queryset(orders_queryset, params.get_value("page"), params.get_value("page_size"))

        weaved_orders = [weave(order) for order in orders]

        return weaved_orders, page_info

    @forge
    @require_permission(Permission.ORDER_CREATE)
    @transaction.atomic
    def post(self, request):
        body = OrderCreateSerializer.validate_request(request)

        print("body", body)

        staff = request.staff
        name = body.get_value("name")
        customer = CustomerService.get_customer_by_id(body.get_value("customer_id"))
        order_date = body.get_value("order_date", timezone.now())
        delivery_date = body.get_value("delivery_date")
        order_items = body.get_value("order_items")
        service_items = body.get_value("service_items", [])
        special_instruction = body.get_value("special_instruction", "")

        # Create Order
        order = OrderService.create_order(customer, staff, name, order_date, delivery_date, special_instruction)

        # Create Order Items and Production Services
        created_order_items = []
        created_service_items = []
        for item in order_items:
            order_item = OrderService.create_order_item(
                order=order,
                card_id=item.get("card_id"),
                discount_amount=item.get("discount_amount", 0),
                quantity=item.get("quantity"),
                requires_box=item.get("requires_box"),
                requires_printing=item.get("requires_printing"),
            )
            order_item_data = model_unwrap(order_item)

            if item.get("requires_box"):
                box_order = BoxOrderService.create_box_order(
                    order_item=order_item, box_type=item.get("box_type"), quantity=item.get("quantity"), total_box_cost=item.get("total_box_cost")
                )
                order_item_data["box_order"] = model_unwrap(box_order)

            if item.get("requires_printing"):
                printing_job = PrintingJobService.create_printing_job(
                    order_item=order_item, quantity=item.get("quantity"), total_printing_cost=item.get("total_printing_cost")
                )
                order_item_data["printing_job"] = model_unwrap(printing_job)

            created_order_items.append(order_item_data)

        # Create Service Items
        for s in service_items or []:
            s_item = ServiceOrderItemService.create_service_item(
                order,
                service_type=s.get("service_type"),
                quantity=s.get("quantity"),
                total_cost=s.get("total_cost"),
                total_expense=s.get("total_expense"),
                description=s.get("description", ""),
            )
            created_service_items.append(model_unwrap(s_item))

        # Create Bill
        bill = BillService.create_bill(order)

        order_data = model_unwrap(order)
        order_data["order_items"] = created_order_items
        order_data["service_items"] = created_service_items

        order_data["bill_id"] = model_unwrap(bill).get("id")

        return order_data

    @forge
    @require_permission(Permission.ORDER_UPDATE)
    @transaction.atomic
    def patch(self, request, order_id):
        body = OrderUpdateSerializer.validate_request(request)

        order = OrderService.get_order_by_id(order_id)

        OrderService.update_order_items(order, body.get_value("order_items"))
        OrderService.remove_order_items(order, body.get_value("remove_item_ids"))
        OrderService.add_order_items(order, body.get_value("add_items"))
        ServiceOrderItemService.update_service_items(order, body.get_value("service_items"))
        ServiceOrderItemService.remove_service_items(order, body.get_value("remove_service_item_ids"))
        ServiceOrderItemService.add_service_items(order, body.get_value("add_service_items"))
        updated_order = OrderService.update_order_misc(
            order, body.get_value("order_status"), body.get_value("delivery_date"), body.get_value("special_instruction")
        )

        order_data = model_unwrap(updated_order)

        bill = BillService.get_bill_by_order_id(order_id)
        order_data["bill_id"] = model_unwrap(bill).get("id")

        return order_data

    @forge
    @require_permission(Permission.ORDER_DELETE)
    @transaction.atomic
    def delete(self, request, order_id):
        OrderService.delete_order(order_id)
        return {"message": "Order deleted successfully"}


class BillView(APIView):
    @forge
    def get(self, request, bill_id=None):
        def weave(bill_details):
            bill_instance = bill_details["bill_instance"]
            detailed_items = bill_details["detailed_order_items"]
            summary = bill_details["summary"]

            # Calculate pending amount = total_with_tax - sum(payments)
            total_paid = bill_instance.payments.aggregate(total=models.Sum("amount")).get("total") or Decimal("0.00")
            summary["pending_amount"] = summary["total_with_tax"] - total_paid

            serialized_order_items = []
            for item_data in detailed_items:
                serialized_item = model_unwrap(item_data["item_details"])
                serialized_item["calculated_costs"] = {k: f"{v:.2f}" for k, v in item_data["calculated_costs"].items()}
                # serialized_item["box_orders"] = model_unwrap(item_data["box_orders"])
                # serialized_item["printing_jobs"] = model_unwrap(item_data["printing_jobs"])
                serialized_order_items.append(serialized_item)

            serialized_bill = model_unwrap(bill_instance)
            serialized_bill["order"] = model_unwrap(bill_instance.order)
            # serialized_bill["order"]["customer"] = model_unwrap(bill_instance.order.customer)
            # serialized_bill["order"]["staff"] = model_unwrap(bill_instance.order.staff)
            serialized_bill["order"]["order_items"] = serialized_order_items
            serialized_bill["summary"] = {k: f"{v:.2f}" for k, v in summary.items()}

            return serialized_bill

        if bill_id:
            bill = BillService.get_bill_by_id(bill_id)
            bill_details = BillService.calculate_bill_details(bill)
            return weave(bill_details)

        params = BillQueryParams.validate_params(request)

        if params.get_value("order_id"):
            bill = BillService.get_bill_by_order_id(params.get_value("order_id"))
            bill_details = BillService.calculate_bill_details(bill)
            return weave(bill_details)

        elif params.get_value("phone"):
            bills_queryset = BillService.get_bills_by_phone(params.get_value("phone"))

        else:
            bills_queryset = BillService.get_bills()

        bills, page_info = PaginationHelper.paginate_queryset(bills_queryset, params.get_value("page"), params.get_value("page_size"))

        detailed_bills = BillService.calculate_bills_details_in_bulk(bills)

        weaved_bills = []
        for bill_details in detailed_bills:
            weaved_bills.append(weave(bill_details))

        return weaved_bills, page_info


class PaymentView(APIView):
    @forge
    def get(self, request, payment_id=None):
        if payment_id:
            payment = PaymentService.get_payment_by_id(payment_id)
            return model_unwrap(payment)

        params = PaymentQueryParams.validate_params(request)

        if params.get_value("bill_id"):
            payments_queryset = PaymentService.get_payments_by_bill_id(params.get_value("bill_id"))

        else:
            payments_queryset = PaymentService.get_payments()

        payments, page_info = PaginationHelper.paginate_queryset(payments_queryset, params.get_value("page"), params.get_value("page_size"))

        return model_unwrap(payments), page_info

    @forge
    def post(self, request):
        body = PaymentCreateSerializer.validate_request(request)
        bill_id = body.get_value("bill_id")

        PaymentService.create_payment(
            bill_id,
            body.get_value("amount"),
            body.get_value("payment_mode"),
            body.get_value("transaction_ref", ""),
            body.get_value("notes", ""),
        )

        BillService.refresh_bill_payment_status(bill_id)

        return {"message": "Payment done successfully"}
