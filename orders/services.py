from decimal import Decimal

from django.conf import settings
from django.db import models, transaction

from core.exceptions import Conflict, ResourceNotFound
from core.utils import model_unwrap
from inventory.services import CardService, InventoryTransactionService
from orders.models import Bill, Order, OrderItem, Payment
from production.models import BoxOrder, PrintingJob


class OrderService:
    @staticmethod
    def get_orders_queryset():
        """
        Returns a base queryset for Orders with all related data pre-fetched for performance.
        """
        return Order.objects.select_related("customer", "staff").prefetch_related(
            models.Prefetch(
                "order_items",
                queryset=OrderItem.objects.select_related("card").prefetch_related(
                    "box_orders",
                    "printing_jobs",
                ),
            )
        )

    @staticmethod
    def get_order_by_id(order_id):
        if not (order := OrderService.get_orders_queryset().filter(id=order_id).first()):
            raise ResourceNotFound("Order not found")

        return order

    @staticmethod
    def get_orders_by_customer_id(customer_id):
        """Get orders filtered by customer ID"""
        return OrderService.get_orders_queryset().filter(customer_id=customer_id).order_by("-created_at")

    @staticmethod
    def get_orders_by_order_date(order_date):
        """Get orders filtered by order date"""
        return OrderService.get_orders_queryset().filter(order_date__date=order_date).order_by("-created_at")

    @staticmethod
    def get_orders():
        """Get all orders ordered by creation date"""
        return OrderService.get_orders_queryset().order_by("-created_at")

    @staticmethod
    def create_order_item(order, card_id, discount_amount, quantity, requires_box, requires_printing):
        card = CardService.get_card_by_id(card_id)

        # Check if the required quantity is available
        if card.quantity < quantity:
            raise Conflict("Quantity in stock is less than the required quantity")

        # Check if the discount amount is less than max discount
        if discount_amount > card.max_discount or discount_amount < 0:
            raise Conflict("Discount amount is not valid")

        card.quantity -= quantity
        card.save()

        order_item = OrderItem.objects.create(
            order=order,
            card=card,
            quantity=quantity,
            price_per_item=card.sell_price,
            discount_amount=discount_amount,
            requires_box=requires_box,
            requires_printing=requires_printing,
        )
        print("Created Order Item \n", model_unwrap(order_item))

        InventoryTransactionService.record_sale_transaction(order_item)

        return order_item

    @staticmethod
    @transaction.atomic
    def create_order(customer, staff, name, order_date, delivery_date, special_instruction):
        if order_date > delivery_date:
            raise Conflict("Order date cannot be greater than delivery date")

        order = Order.objects.create(
            name=name,
            customer=customer,
            staff=staff,
            order_date=order_date,
            delivery_date=delivery_date,
            special_instruction=special_instruction,
        )
        print("Created Order \n", model_unwrap(order))

        return order


class BillService:
    @staticmethod
    def check_bill_exists(bill_id):
        return Bill.objects.filter(id=bill_id).exists()

    @staticmethod
    def get_bill_by_id(bill_id):
        bill = Bill.objects.select_related("order", "order__customer", "order__staff").filter(id=bill_id).first()
        if not bill:
            raise ResourceNotFound("Bill not found")

        return bill
        # return BillService.calculate_bill_details(bill)

    @staticmethod
    def get_bills_by_order_id(order_id):
        """Get bills for a given order ID"""
        return Bill.objects.filter(order_id=order_id).select_related("order", "order__customer", "order__staff").order_by("-created_at")

    @staticmethod
    def get_bills():
        """Get all bills"""
        return Bill.objects.select_related("order", "order__customer", "order__staff").all().order_by("-created_at")

    @staticmethod
    def get_bill_by_phone(phone):
        """Get bills by customer phone number"""
        return Bill.objects.select_related("order", "order__customer").filter(order__customer__phone=phone).order_by("-created_at")

    @staticmethod
    def create_bill(order):
        if Bill.objects.filter(order=order).exists():
            raise Conflict("Bill already exists")

        bill = Bill.objects.create(
            order=order,
            tax_percentage=settings.TAX_PERCENTAGE,
        )
        return bill

    @staticmethod
    def calculate_bill_details(bill, prefetched_data=None):
        """
        Calculates the total costs for a single bill.
        Can use prefetched data for optimization in bulk operations.
        """
        order = bill.order

        if prefetched_data:
            current_order_items = prefetched_data["order_items_map"].get(order.id, [])
            box_orders_map = prefetched_data["box_orders_map"]
            printing_jobs_map = prefetched_data["printing_jobs_map"]
        else:
            # This path is taken when calculating for a single bill without pre-fetching.
            current_order_items = order.order_items.all().select_related("card")
            item_ids = [item.id for item in current_order_items]
            box_orders = BoxOrder.objects.filter(order_item_id__in=item_ids)
            printing_jobs = PrintingJob.objects.filter(order_item_id__in=item_ids)

            box_orders_map = {item.id: [] for item in current_order_items}
            for bo in box_orders:
                box_orders_map.setdefault(bo.order_item_id, []).append(bo)

            printing_jobs_map = {item.id: [] for item in current_order_items}
            for pj in printing_jobs:
                printing_jobs_map.setdefault(pj.order_item_id, []).append(pj)

        items_total = Decimal("0.00")
        total_box_cost = Decimal("0.00")
        total_printing_cost = Decimal("0.00")
        detailed_order_items = []

        for item in current_order_items:
            item_base_cost = (item.price_per_item - item.discount_amount) * item.quantity

            item_box_orders = box_orders_map.get(item.id, [])
            item_printing_jobs = printing_jobs_map.get(item.id, [])

            item_box_costs = sum(bo.total_box_cost for bo in item_box_orders if bo.total_box_cost)
            item_printing_costs = sum(pj.total_printing_cost for pj in item_printing_jobs if pj.total_printing_cost)

            items_total += item_base_cost
            total_box_cost += item_box_costs
            total_printing_cost += item_printing_costs

            detailed_order_items.append(
                {
                    "item_details": item,
                    "calculated_costs": {
                        "base_cost": item_base_cost,
                        "box_cost": item_box_costs,
                        "printing_cost": item_printing_costs,
                        "total_cost": item_base_cost + item_box_costs + item_printing_costs,
                    },
                    "box_orders": item_box_orders,
                    "printing_jobs": item_printing_jobs,
                }
            )

        grand_total = items_total + total_box_cost + total_printing_cost
        tax_amount = grand_total * (bill.tax_percentage / Decimal("100.0"))
        total_with_tax = grand_total + tax_amount

        return {
            "bill_instance": bill,
            "detailed_order_items": detailed_order_items,
            "summary": {
                "items_subtotal": items_total,
                "total_box_cost": total_box_cost,
                "total_printing_cost": total_printing_cost,
                "grand_total": grand_total,
                "tax_percentage": bill.tax_percentage,
                "tax_amount": tax_amount,
                "total_with_tax": total_with_tax,
            },
        }

    @staticmethod
    def calculate_bills_details_in_bulk(bills):
        """
        Efficiently fetches details for a list of bills and calculates their totals.
        """
        if not bills:
            return []

        order_ids = [bill.order_id for bill in bills]
        all_order_items = OrderItem.objects.filter(order_id__in=order_ids).select_related("card")
        order_item_ids = [item.id for item in all_order_items]

        box_orders = BoxOrder.objects.filter(order_item_id__in=order_item_ids)
        printing_jobs = PrintingJob.objects.filter(order_item_id__in=order_item_ids)

        order_items_map: dict[int, list[OrderItem]] = {}
        for item in all_order_items:
            order_items_map.setdefault(item.order_id, []).append(item)

        box_orders_map: dict[int, list[BoxOrder]] = {}
        for bo in box_orders:
            box_orders_map.setdefault(bo.order_item_id, []).append(bo)

        printing_jobs_map: dict[int, list[PrintingJob]] = {}
        for pj in printing_jobs:
            printing_jobs_map.setdefault(pj.order_item_id, []).append(pj)

        prefetched_data = {"order_items_map": order_items_map, "box_orders_map": box_orders_map, "printing_jobs_map": printing_jobs_map}

        results = []
        for bill in bills:
            results.append(BillService.calculate_bill_details(bill, prefetched_data))

        return results

    @staticmethod
    def refresh_bill_payment_status(bill_id):
        """
        Recalculates and updates the payment status of a bill based on associated payments.
        """
        bill = BillService.get_bill_by_id(bill_id)
        bill_details = BillService.calculate_bill_details(bill)
        total_due = bill_details["summary"]["total_with_tax"]

        payments = Payment.objects.filter(bill=bill)
        total_paid = payments.aggregate(total=models.Sum("amount"))["total"] or Decimal("0.00")

        new_status = Bill.PaymentStatus.PENDING
        if total_paid >= total_due:
            new_status = Bill.PaymentStatus.PAID
        elif total_paid > 0:
            new_status = Bill.PaymentStatus.PARTIAL

        if bill.payment_status != new_status:
            bill.payment_status = new_status
            bill.save(update_fields=["payment_status", "updated_at"])

        return bill


class PaymentService:
    @staticmethod
    def get_payment_by_id(payment_id):
        if not (payment := Payment.objects.filter(id=payment_id).first()):
            raise ResourceNotFound("Payment not found")

        return payment

    @staticmethod
    def get_payments_by_bill_id(bill_id):
        return Payment.objects.filter(bill=bill_id).order_by("-created_at")

    @staticmethod
    def get_payments():
        return Payment.objects.all().order_by("-created_at")

    @staticmethod
    def create_payment(bill_id, amount, payment_mode, transaction_ref, notes):
        if not BillService.check_bill_exists(bill_id):
            raise ResourceNotFound("Bill not found")

        payment = Payment.objects.create(
            bill_id=bill_id,
            amount=amount,
            payment_mode=payment_mode,
            transaction_ref=transaction_ref,
            notes=notes,
        )

        return payment
