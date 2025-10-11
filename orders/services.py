from decimal import Decimal

from django.conf import settings
from django.db import models, transaction

from core.exceptions import Conflict, ResourceNotFound
from core.utils import model_unwrap
from inventory.models import Card
from inventory.services import InventoryTransactionService
from orders.models import Bill, BillAdjustment, Order, OrderItem, Payment, ServiceOrderItem
from production.models import BoxOrder, PrintingJob


class OrderService:
    @staticmethod
    def get_orders_queryset():
        return Order.objects.select_related("customer", "staff").prefetch_related(
            models.Prefetch(
                "order_items",
                queryset=OrderItem.objects.select_related("card").prefetch_related(
                    "box_orders",
                    "printing_jobs",
                    "inventory_transactions",
                ),
            ),
            "service_items",
        )

    @staticmethod
    def get_order_by_id(order_id):
        if not (order := OrderService.get_orders_queryset().filter(id=order_id).first()):
            raise ResourceNotFound("Order not found")

        return order

    @staticmethod
    def get_orders(*, customer_id=None, order_date=None):
        qs = OrderService.get_orders_queryset()
        if customer_id:
            qs = qs.filter(customer_id=customer_id)
        if order_date:
            qs = qs.filter(order_date__date=order_date)
        return qs.order_by("-created_at")

    @staticmethod
    def create_order_item(order, card_id, discount_amount, quantity, requires_box, requires_printing):
        card = Card.objects.select_for_update().filter(id=card_id, is_active=True).first()
        if not card:
            raise ResourceNotFound("Card not found")
        if card.quantity < quantity:
            raise Conflict("Quantity in stock is less than the required quantity")

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

        return order

    @staticmethod
    def update_order_items(order, order_items):
        def _adjust_order_item_quantity(order_item, new_quantity):
            if new_quantity is None or new_quantity == order_item.quantity:
                return
            delta = new_quantity - order_item.quantity
            locked_card = Card.objects.select_for_update().filter(id=order_item.card_id).first()
            if not locked_card:
                raise ResourceNotFound("Card not found")
            if delta > 0:
                if locked_card.quantity < delta:
                    raise Conflict("Quantity in stock is less than the required quantity")
                locked_card.quantity -= delta
            elif delta < 0:
                locked_card.quantity += -delta
            locked_card.save()
            order_item.quantity = new_quantity

        def _update_discount(order_item, discount_amount):
            if discount_amount is None:
                return
            if discount_amount > order_item.card.max_discount or discount_amount < 0:
                raise Conflict("Discount amount is not valid")
            order_item.discount_amount = discount_amount

        def _handle_box_requirements(order_item, requires_box, box_type, total_box_cost):
            previous = order_item.requires_box
            if requires_box is not None:
                if previous and not requires_box:
                    from production.services import BoxOrderService

                    BoxOrderService.delete_by_order_item(order_item)
                order_item.requires_box = requires_box
                if not previous and requires_box:
                    from production.services import BoxOrderService

                    BoxOrderService.create_box_order(order_item, box_type, order_item.quantity, total_box_cost)
            if (
                (box_type is not None or total_box_cost is not None)
                and (order_item.requires_box or requires_box is True)
                and requires_box is not False
            ):
                from production.services import BoxOrderService

                current = BoxOrderService.get_latest_by_order_item_id(order_item.id)
                if current:
                    BoxOrderService.update_box_order(current, box_type=box_type, total_box_cost=total_box_cost)

        def _handle_printing_requirements(order_item, requires_printing, total_printing_cost):
            previous = order_item.requires_printing
            if requires_printing is not None:
                if previous and not requires_printing:
                    from production.services import PrintingJobService

                    PrintingJobService.delete_by_order_item(order_item)
                order_item.requires_printing = requires_printing
                if not previous and requires_printing:
                    from production.services import PrintingJobService

                    PrintingJobService.create_printing_job(order_item, order_item.quantity, total_printing_cost)
            if total_printing_cost is not None and (order_item.requires_printing or requires_printing is True) and requires_printing is not False:
                from production.services import PrintingJobService

                current = PrintingJobService.get_latest_by_order_item_id(order_item.id)
                if current:
                    PrintingJobService.update_printing_job(current, total_printing_cost=total_printing_cost)

        for item in order_items or []:
            order_item = OrderItem.objects.get(id=item.get("order_item_id"), order=order)
            _adjust_order_item_quantity(order_item, item.get("quantity"))
            _update_discount(order_item, item.get("discount_amount"))
            _handle_box_requirements(order_item, item.get("requires_box"), item.get("box_type"), item.get("total_box_cost"))
            _handle_printing_requirements(order_item, item.get("requires_printing"), item.get("total_printing_cost"))
            order_item.save()
        # Recalculate order status after item updates
        OrderStatusService.mark_in_progress_if_started(order)
        OrderStatusService.recalculate_ready(order)
        return order

    @staticmethod
    def remove_order_items(order, remove_item_ids):
        for oid in remove_item_ids or []:
            order_item = OrderItem.objects.get(id=oid, order=order)
            InventoryTransactionService.record_return_transaction(order_item)
            locked_card = Card.objects.select_for_update().filter(id=order_item.card_id).first()
            if not locked_card:
                raise ResourceNotFound("Card not found")
            locked_card.quantity += order_item.quantity
            locked_card.save()
            order_item.delete()
        # Removing items may affect READY status
        OrderStatusService.recalculate_ready(order)
        return order

    @staticmethod
    def add_order_items(order, add_items):
        for item in add_items or []:
            order_item = OrderService.create_order_item(
                order=order,
                card_id=item.get("card_id"),
                discount_amount=item.get("discount_amount"),
                quantity=item.get("quantity"),
                requires_box=item.get("requires_box"),
                requires_printing=item.get("requires_printing"),
            )
            if item.get("requires_box"):
                from production.services import BoxOrderService

                BoxOrderService.create_box_order(order_item, item.get("box_type"), item.get("quantity"), item.get("total_box_cost"))
            if item.get("requires_printing"):
                from production.services import PrintingJobService

                PrintingJobService.create_printing_job(order_item, item.get("quantity"), item.get("total_printing_cost"))
        # Adding items might kick off work → IN_PROGRESS
        OrderStatusService.mark_in_progress_if_started(order)
        OrderStatusService.recalculate_ready(order)
        return order

    @staticmethod
    def update_order_misc(order, order_status, delivery_date, special_instruction, name=None):
        if delivery_date and order.order_date and order.order_date > delivery_date:
            raise Conflict("Order date cannot be greater than delivery date")
        order.order_status = order_status or order.order_status
        order.delivery_date = delivery_date or order.delivery_date
        order.special_instruction = special_instruction or order.special_instruction
        if name is not None and name != "":
            order.name = name
        order.save()
        # If status not explicitly provided, try to keep it consistent
        if not order_status:
            OrderStatusService.mark_in_progress_if_started(order)
            OrderStatusService.recalculate_ready(order)
        return order

    @staticmethod
    def delete_order(order_id: str) -> None:
        """Delete an order and all of its dependent records safely.

        Steps:
        - Prevent deletion if there are any payments or bill adjustments.
        - Revert inventory quantities for each order item and record return transactions.
        - Rely on database cascades to remove dependent rows (order items, service items, bill, payments, production jobs).
        """
        order = OrderService.get_order_by_id(order_id)

        # Guard: do not allow deleting orders with any payments or adjustments recorded
        bill = Bill.objects.filter(order=order).first()
        if bill:
            if Payment.objects.filter(bill=bill).exists():
                raise Conflict("Cannot delete order with payments. Refund or delete payments first.")
            if BillAdjustment.objects.filter(bill=bill).exists():
                raise Conflict("Cannot delete order with bill adjustments. Remove adjustments first.")

        # Revert inventory for all order items
        order_items = OrderItem.objects.filter(order=order).select_related("card")
        for order_item in order_items:
            # Record the return transaction then add quantity back
            InventoryTransactionService.record_return_transaction(order_item)

            locked_card = Card.objects.select_for_update().filter(id=order_item.card_id).first()
            if not locked_card:
                raise ResourceNotFound("Card not found")
            locked_card.quantity += order_item.quantity
            locked_card.save()

        # Finally delete the order (cascades will handle children)
        order.delete()


class OrderStatusService:
    @staticmethod
    def mark_in_progress_if_started(order: Order) -> bool:
        """
        If any work has effectively started (provider assigned or any subtask in progress),
        bump order status from CONFIRMED to IN_PROGRESS.
        Returns True if status changed.
        """
        if order.order_status != Order.OrderStatus.CONFIRMED:
            return False

        # Check printing jobs and box orders for any assignment/progress
        has_progress = False
        for item in order.order_items.all():
            # Printing started if printer or tracing studio assigned, or status moved from PENDING
            printing_jobs = getattr(item, "printing_jobs", None)
            if printing_jobs:
                for pj in printing_jobs.all():
                    if pj.printer_id or pj.tracing_studio_id:
                        has_progress = True
                        break
                    if pj.printing_status != pj.PrintingStatus.PENDING:
                        has_progress = True
                        break
            if has_progress:
                break

            # Box started if box maker assigned, or status moved from PENDING
            box_orders = getattr(item, "box_orders", None)
            if box_orders:
                for bo in box_orders.all():
                    if bo.box_maker_id:
                        has_progress = True
                        break
                    if bo.box_status != bo.BoxStatus.PENDING:
                        has_progress = True
                        break
            if has_progress:
                break

        if has_progress:
            order.order_status = Order.OrderStatus.IN_PROGRESS
            order.save(update_fields=["order_status", "updated_at"])
            return True
        return False

    @staticmethod
    def recalculate_ready(order: Order) -> bool:
        """
        Set order to READY if all required production/service tasks are completed.
        Returns True if status changed.
        """
        # Only attempt READY if not already DELIVERED or FULLY_PAID (terminal states)
        if order.order_status in (Order.OrderStatus.DELIVERED, Order.OrderStatus.FULLY_PAID):
            return False

        # Must be at least IN_PROGRESS to reach READY
        current_status = order.order_status

        def item_ready(oi: OrderItem) -> bool:
            if oi.requires_printing:
                printing_jobs = oi.printing_jobs.all()
                if not printing_jobs:
                    return False
                if any(pj.printing_status != pj.PrintingStatus.COMPLETED for pj in printing_jobs):
                    return False
            if oi.requires_box:
                box_orders = oi.box_orders.all()
                if not box_orders:
                    return False
                if any(bo.box_status != bo.BoxStatus.COMPLETED for bo in box_orders):
                    return False
            return True

        # All order items that require work should be ready
        for oi in order.order_items.all():
            if oi.requires_printing or oi.requires_box:
                if not item_ready(oi):
                    return False

        # Optional: third-party service items readiness (treat DELIVERED as ready)
        for si in order.service_items.all():
            if si.procurement_status != ServiceOrderItem.ProcurementStatus.DELIVERED:
                return False

        if current_status != Order.OrderStatus.READY:
            order.order_status = Order.OrderStatus.READY
            order.save(update_fields=["order_status", "updated_at"])
            return True
        return False


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

    @staticmethod
    def get_bill_by_order_id(order_id):
        bill = Bill.objects.select_related("order", "order__customer", "order__staff").filter(order_id=order_id).first()
        if not bill:
            raise ResourceNotFound("Bill not found")
        return bill

    @staticmethod
    def get_bills():
        return Bill.objects.select_related("order", "order__customer", "order__staff").all().order_by("-created_at")

    @staticmethod
    def get_bills_by_phone(phone):
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
        order = bill.order

        if prefetched_data:
            current_order_items = prefetched_data["order_items_map"].get(order.id, [])
            box_orders_map = prefetched_data["box_orders_map"]
            printing_jobs_map = prefetched_data["printing_jobs_map"]
            service_items = prefetched_data.get("service_items_map", {}).get(order.id, [])
        else:
            # This path is taken when calculating for a single bill without pre-fetching.
            current_order_items = order.order_items.all().select_related("card")
            item_ids = [item.id for item in current_order_items]
            box_orders = BoxOrder.objects.filter(order_item_id__in=item_ids)
            printing_jobs = PrintingJob.objects.filter(order_item_id__in=item_ids)
            service_items = ServiceOrderItem.objects.filter(order=order)

            box_orders_map = {item.id: [] for item in current_order_items}
            for bo in box_orders:
                box_orders_map.setdefault(bo.order_item_id, []).append(bo)

            printing_jobs_map = {item.id: [] for item in current_order_items}
            for pj in printing_jobs:
                printing_jobs_map.setdefault(pj.order_item_id, []).append(pj)

        items_total = Decimal("0.00")
        service_items_total = Decimal("0.00")
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

        # Include service items as additional detailed items
        for s_item in service_items:
            base_cost = s_item.total_cost or Decimal("0.00")
            service_items_total += base_cost
            detailed_order_items.append(
                {
                    "item_details": s_item,
                    "calculated_costs": {
                        "base_cost": base_cost,
                        "box_cost": Decimal("0.00"),
                        "printing_cost": Decimal("0.00"),
                        "total_cost": base_cost,
                    },
                    "box_orders": [],
                    "printing_jobs": [],
                }
            )

        grand_total = items_total + service_items_total + total_box_cost + total_printing_cost
        tax_amount = grand_total * (bill.tax_percentage / Decimal("100.0"))
        total_with_tax = grand_total + tax_amount

        return {
            "bill_instance": bill,
            "detailed_order_items": detailed_order_items,
            "summary": {
                "order_items_subtotal": items_total,
                "service_items_subtotal": service_items_total,
                "items_subtotal": items_total + service_items_total,
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
        if not bills:
            return []

        order_ids = [bill.order_id for bill in bills]
        all_order_items = OrderItem.objects.filter(order_id__in=order_ids).select_related("card")
        order_item_ids = [item.id for item in all_order_items]

        box_orders = BoxOrder.objects.filter(order_item_id__in=order_item_ids)
        printing_jobs = PrintingJob.objects.filter(order_item_id__in=order_item_ids)
        all_service_items = ServiceOrderItem.objects.filter(order_id__in=order_ids)

        order_items_map: dict[int, list[OrderItem]] = {}
        for item in all_order_items:
            order_items_map.setdefault(item.order_id, []).append(item)

        box_orders_map: dict[int, list[BoxOrder]] = {}
        for bo in box_orders:
            box_orders_map.setdefault(bo.order_item_id, []).append(bo)

        printing_jobs_map: dict[int, list[PrintingJob]] = {}
        for pj in printing_jobs:
            printing_jobs_map.setdefault(pj.order_item_id, []).append(pj)

        service_items_map: dict[int, list[ServiceOrderItem]] = {}
        for si in all_service_items:
            service_items_map.setdefault(si.order_id, []).append(si)

        prefetched_data = {
            "order_items_map": order_items_map,
            "box_orders_map": box_orders_map,
            "printing_jobs_map": printing_jobs_map,
            "service_items_map": service_items_map,
        }

        results = []
        for bill in bills:
            results.append(BillService.calculate_bill_details(bill, prefetched_data))

        return results

    @staticmethod
    def refresh_bill_payment_status(bill_id):
        bill = BillService.get_bill_by_id(bill_id)
        bill_details = BillService.calculate_bill_details(bill)
        total_due = bill_details["summary"]["total_with_tax"]

        payments = Payment.objects.filter(bill=bill)
        total_paid = payments.aggregate(total=models.Sum("amount"))["total"] or Decimal("0.00")

        # Include bill adjustments as eligible credits towards payment status
        adjustments = BillAdjustment.objects.filter(bill=bill)
        total_adjusted = adjustments.aggregate(total=models.Sum("amount"))["total"] or Decimal("0.00")

        total_credited = total_paid + total_adjusted

        new_status = Bill.PaymentStatus.PENDING
        if total_credited >= total_due:
            new_status = Bill.PaymentStatus.PAID
        elif total_credited > 0:
            new_status = Bill.PaymentStatus.PARTIAL

        if bill.payment_status != new_status:
            bill.payment_status = new_status
            bill.save(update_fields=["payment_status", "updated_at"])

            # Sync Order status with payment status per business rule:
            # - If PAID -> set Order to FULLY_PAID (terminal/done), unless already DELIVERED
            # - If PARTIAL/PENDING -> do not downgrade Order status
            order = bill.order
            if new_status == Bill.PaymentStatus.PAID:
                if order.order_status != Order.OrderStatus.DELIVERED and order.order_status != Order.OrderStatus.FULLY_PAID:
                    order.order_status = Order.OrderStatus.FULLY_PAID
                    order.save(update_fields=["order_status", "updated_at"])

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


class BillAdjustmentService:
    @staticmethod
    def get_adjustment_by_id(adjustment_id):
        adjustment = BillAdjustment.objects.select_related("bill", "staff").filter(id=adjustment_id).first()
        if not adjustment:
            from core.exceptions import ResourceNotFound

            raise ResourceNotFound("Bill Adjustment not found")
        return adjustment

    @staticmethod
    def get_adjustments_by_bill_id(bill_id):
        return BillAdjustment.objects.filter(bill_id=bill_id).select_related("staff").order_by("-created_at")

    @staticmethod
    def get_adjustments():
        return BillAdjustment.objects.all().select_related("staff").order_by("-created_at")

    @staticmethod
    def create_adjustment(*, bill_id: str, staff, adjustment_type: str, amount: Decimal, reason: str) -> BillAdjustment:
        if not BillService.check_bill_exists(bill_id):
            from core.exceptions import ResourceNotFound

            raise ResourceNotFound("Bill not found")

        adjustment = BillAdjustment.objects.create(
            bill_id=bill_id,
            staff=staff,
            adjustment_type=adjustment_type,
            amount=amount,
            reason=reason,
        )
        return adjustment


class ServiceOrderItemService:
    @staticmethod
    def create_service_item(
        order: Order, *, service_type: str, quantity: int, total_cost: Decimal, total_expense: Decimal | None = None, description: str = ""
    ):
        if quantity is None or quantity <= 0:
            raise Conflict("Quantity must be greater than zero")

        item = ServiceOrderItem.objects.create(
            order=order,
            service_type=service_type,
            quantity=quantity,
            total_cost=total_cost,
            total_expense=total_expense,
            description=description or "",
        )
        return item

    @staticmethod
    def update_service_items(order: Order, items: list[dict] | None):
        for payload in items or []:
            s_item = ServiceOrderItem.objects.get(id=payload.get("service_order_item_id"), order=order)

            quantity = payload.get("quantity")
            if quantity is not None:
                if quantity <= 0:
                    raise Conflict("Quantity must be greater than zero")
                s_item.quantity = quantity

            if (status := payload.get("procurement_status")) is not None:
                s_item.procurement_status = status

            if (total_cost := payload.get("total_cost")) is not None:
                s_item.total_cost = total_cost

            if "total_expense" in payload:
                s_item.total_expense = payload.get("total_expense")

            if (desc := payload.get("description")) is not None:
                s_item.description = desc

            s_item.save()
        # Service items may affect READY status
        OrderStatusService.mark_in_progress_if_started(order)
        OrderStatusService.recalculate_ready(order)
        return order

    @staticmethod
    def add_service_items(order: Order, add_items: list[dict] | None):
        for payload in add_items or []:
            service_type = payload.get("service_type")
            quantity = payload.get("quantity")
            total_cost = payload.get("total_cost")

            if not service_type or not isinstance(service_type, str):
                raise Conflict("Service type is required and must be a string")
            if quantity is None or not isinstance(quantity, int):
                raise Conflict("Quantity is required and must be an integer")
            if total_cost is None or not isinstance(total_cost, Decimal):
                raise Conflict("Total cost is required and must be a decimal")

            ServiceOrderItemService.create_service_item(
                order,
                service_type=service_type,
                quantity=quantity,
                total_cost=total_cost,
                total_expense=payload.get("total_expense"),
                description=payload.get("description", ""),
            )
        OrderStatusService.mark_in_progress_if_started(order)
        OrderStatusService.recalculate_ready(order)
        return order

    @staticmethod
    def remove_service_items(order: Order, remove_item_ids: list[str] | None):
        for sid in remove_item_ids or []:
            ServiceOrderItem.objects.filter(id=sid, order=order).delete()
        OrderStatusService.recalculate_ready(order)
        return order
