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
        if not (order_items := OrderItem.objects.filter(order=order_id)):
            raise ResourceNotFound("Order items not found")

        return order_items


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
