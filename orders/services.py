from django.conf import settings
from django.db import transaction

from core.exceptions import Conflict, ResourceNotFound
from core.utils import model_unwrap
from inventory.services import CardService, InventoryTransactionService
from orders.models import Bill, Order, OrderItem


class OrderService:
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

        InventoryTransactionService.record_sale_transaction(card, quantity, order.staff)

        return order_item

    @staticmethod
    @transaction.atomic
    def create_order(customer, staff, order_date, delivery_date, special_instruction):
        order = Order.objects.create(
            customer=customer,
            staff=staff,
            order_date=order_date,
            delivery_date=delivery_date,
            special_instruction=special_instruction,
        )
        print("Created Order \n", model_unwrap(order))

        return order

    @staticmethod
    def get_order_by_id(order_id):
        if not (order := Order.objects.filter(id=order_id).first()):
            raise ResourceNotFound("Order not found")

        return order

    @staticmethod
    def get_order_items_by_order_id(order_id):
        """Get order items for a specific order"""
        return OrderItem.objects.filter(order=order_id)

    @staticmethod
    def get_orders_by_customer_id(customer_id):
        """Get orders filtered by customer ID"""
        return Order.objects.filter(customer_id=customer_id).order_by("-created_at")

    @staticmethod
    def get_orders_by_order_date(order_date):
        """Get orders filtered by order date"""
        return Order.objects.filter(order_date__date=order_date).order_by("-created_at")

    @staticmethod
    def get_orders():
        """Get all orders ordered by creation date"""
        return Order.objects.all().order_by("-created_at")

    @staticmethod
    def get_order_with_items(order_id):
        """Get order with all related data efficiently"""
        order = OrderService.get_order_by_id(order_id)
        order_items = OrderService.get_order_items_by_order_id(order_id)
        return order, order_items

    @staticmethod
    def get_orders_with_items_bulk(orders):
        """Get multiple orders with their items using bulk queries"""
        # Get all order IDs
        order_ids = [order.id for order in orders]

        # Get all order items for these orders in one query
        all_order_items = OrderItem.objects.filter(order_id__in=order_ids)

        # Group order items by order_id
        order_items_map: dict[int, list[OrderItem]] = {}
        for item in all_order_items:
            if item.order_id not in order_items_map:
                order_items_map[item.order_id] = []
            order_items_map[item.order_id].append(item)

        # Create result with orders and their items
        result = []
        for order in orders:
            order_items = order_items_map.get(order.id, [])
            result.append({"order": order, "order_items": order_items})

        return result


class BillService:
    @staticmethod
    def create_bill(order):
        if BillService.check_bill_exists(order):
            raise Conflict("Bill already exists")

        bill = Bill.objects.create(
            order=order,
            tax_percentage=settings.TAX_PERCENTAGE,
        )
        return bill

    @staticmethod
    def check_bill_exists(order):
        if bill := Bill.objects.filter(order=order).first():
            raise Conflict("Bill already exists")

        return bill
