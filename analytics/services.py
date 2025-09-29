from datetime import date, timedelta
from decimal import Decimal

from dateutil.relativedelta import relativedelta  # type: ignore
from django.conf import settings
from django.db.models import Q, Sum, Count, Max, Min, F, OuterRef, Subquery, DecimalField, ExpressionWrapper
from django.utils import timezone

from inventory.models import Card, InventoryTransaction
from orders.models import Bill, Order, OrderItem
from core.constants import PRICE_DECIMAL_PLACES
from orders.services import OrderService
from production.models import BoxOrder, PrintingJob


class AnalyticsService:
    @staticmethod
    def get_low_stock_items():
        return Card.objects.filter(quantity__gt=settings.OUT_OF_STOCK_THRESHOLD, quantity__lte=settings.LOW_STOCK_THRESHOLD, is_active=True).count()

    @staticmethod
    def get_out_of_stock_items():
        return Card.objects.filter(quantity__lte=settings.OUT_OF_STOCK_THRESHOLD, is_active=True).count()

    @staticmethod
    def get_total_orders_current_month():
        today = timezone.now().date()
        start_of_month = today.replace(day=1)
        # To get the end of the month, we can find the first day of the next month and subtract one day.
        next_month_start = (start_of_month.replace(day=28) + timedelta(days=4)).replace(day=1)
        end_of_month = next_month_start - timedelta(days=1)
        return Order.objects.filter(order_date__date__range=[start_of_month, end_of_month]).count()

    @staticmethod
    def get_monthly_order_change():
        today = timezone.now().date()

        # Current month orders
        current_month_start = today.replace(day=1)
        next_month_start = (current_month_start.replace(day=28) + timedelta(days=4)).replace(day=1)
        current_month_end = next_month_start - timedelta(days=1)
        current_month_orders = Order.objects.filter(order_date__date__range=[current_month_start, current_month_end]).count()

        # Previous month orders
        prev_month_end = current_month_start - timedelta(days=1)
        prev_month_start = prev_month_end.replace(day=1)
        previous_month_orders = Order.objects.filter(order_date__date__range=[prev_month_start, prev_month_end]).count()

        if previous_month_orders == 0:
            return 100.0 if current_month_orders > 0 else 0.0

        change = ((current_month_orders - previous_month_orders) / previous_month_orders) * 100
        return round(change, 2)

    @staticmethod
    def get_pending_orders():
        return Order.objects.exclude(order_status__in=[Order.OrderStatus.DELIVERED, Order.OrderStatus.FULLY_PAID]).count()

    @staticmethod
    def get_todays_orders(today: date):
        return Order.objects.filter(order_date__date=today).count()

    @staticmethod
    def get_pending_bills_count():
        return Bill.objects.filter(Q(payment_status=Bill.PaymentStatus.PENDING) | Q(payment_status=Bill.PaymentStatus.PARTIAL)).count()

    @staticmethod
    def _calculate_profit_for_period(start_date, end_date):
        """
        A helper method to calculate gross profit and pending orders for a specific time period.
        It checks if all production expenses have been logged before including an order in the calculation.
        """
        # Get all orders created in the specified period
        period_orders = Order.objects.filter(order_date__date__range=[start_date, end_date]).prefetch_related(
            "order_items__card",
            "order_items__printing_jobs",
            "order_items__box_orders",
            "order_items__inventory_transactions",
            "service_items",
        )

        total_profit = Decimal("0.0")
        pending_orders_count = 0

        for order in period_orders:
            is_ready_for_calculation = True
            current_order_profit = Decimal("0.0")

            for item in order.order_items.all():
                # Check if all required expenses are logged
                if item.requires_printing:
                    for job in item.printing_jobs.all():
                        if job.total_printing_expense is None or job.total_tracing_expense is None:
                            is_ready_for_calculation = False
                            break
                if not is_ready_for_calculation:
                    break

                if item.requires_box:
                    for box in item.box_orders.all():
                        if box.total_box_expense is None:
                            is_ready_for_calculation = False
                            break
                if not is_ready_for_calculation:
                    break

                # If ready, calculate profit for this item using transaction-linked cost when available
                inventory_transactions = getattr(item, "inventory_transactions", None)
                if inventory_transactions and hasattr(inventory_transactions, "all"):
                    transactions = inventory_transactions.all()
                else:
                    transactions = []

                sale_tx = next(
                    (tx for tx in transactions if tx.transaction_type == InventoryTransaction.TransactionType.SALE),
                    None,
                )
                effective_cost_price = sale_tx.cost_price if sale_tx else item.card.cost_price
                card_sale_profit = (item.price_per_item - item.discount_amount - effective_cost_price) * item.quantity
                current_order_profit += card_sale_profit

                for job in item.printing_jobs.all():
                    current_order_profit += job.total_printing_cost - (job.total_printing_expense + job.total_tracing_expense)

                for box in item.box_orders.all():
                    current_order_profit += box.total_box_cost - box.total_box_expense

            if not is_ready_for_calculation:
                pending_orders_count += 1
                continue

            # Include third-party service items (must have total_expense to finalize)
            for s_item in order.service_items.all():
                if s_item.total_expense is None:
                    is_ready_for_calculation = False
                    break
                current_order_profit += s_item.total_cost - s_item.total_expense

            if is_ready_for_calculation:
                total_profit += current_order_profit
            else:
                pending_orders_count += 1

        return {"profit": total_profit, "orders_pending_expense_logging": pending_orders_count}

    @staticmethod
    def get_monthly_profit_analysis():
        """
        Calculates the estimated gross profit for all orders created within the current calendar month.
        This method uses an accrual-based approach, meaning profit is recognized when the order is
        created, not when it's paid. This gives a better view of the month's business performance.
        CRITICAL: To ensure accuracy, an order is only included in the profit calculation after all
        of its production expenses (for printing, tracing, and boxes) have been logged in the system.
        This prevents showing inflated profit numbers before all costs are known.
        Returns two values:
        1. 'monthly_profit': The calculated profit so far for all qualifying orders this month.
        2. 'orders_pending_expense_logging': A count of orders from this month that are still
           awaiting expense data and are therefore not yet included in the profit figure.
        """
        today = timezone.now().date()
        start_of_month = today.replace(day=1)
        next_month_start = (start_of_month.replace(day=28) + timedelta(days=4)).replace(day=1)
        end_of_month = next_month_start - timedelta(days=1)
        profit_data = AnalyticsService._calculate_profit_for_period(start_of_month, end_of_month)

        return {
            "monthly_profit": profit_data["profit"],
            "orders_pending_expense_logging": profit_data["orders_pending_expense_logging"],
        }

    @staticmethod
    def get_yearly_profit_analysis():
        """
        Calculates the gross profit for each of the last 12 months.
        This is perfect for powering a year-over-year profit chart.
        """
        today = timezone.now().date()
        yearly_data = []
        for i in range(12):
            # Calculate start and end date for each of the last 12 months
            month_date = today - relativedelta(months=i)
            start_of_month = month_date.replace(day=1)
            next_month_start = (start_of_month.replace(day=28) + timedelta(days=4)).replace(day=1)
            end_of_month = next_month_start - timedelta(days=1)

            # Use the helper function to calculate profit for that month
            profit_data = AnalyticsService._calculate_profit_for_period(start_of_month, end_of_month)

            yearly_data.append({"month": start_of_month.strftime("%Y-%m"), "profit": f"{profit_data['profit']:.2f}"})

        return yearly_data[::-1]  # Reverse to get oldest month first

    @staticmethod
    def get_pending_production_counts():
        pending_printing = PrintingJob.objects.exclude(printing_status=PrintingJob.PrintingStatus.COMPLETED).count()
        pending_boxing = BoxOrder.objects.exclude(box_status=BoxOrder.BoxStatus.COMPLETED).count()
        return pending_printing, pending_boxing

    @staticmethod
    def get_low_stock_cards_list():
        return Card.objects.filter(
            quantity__gt=settings.OUT_OF_STOCK_THRESHOLD, quantity__lte=settings.LOW_STOCK_THRESHOLD, is_active=True
        ).select_related("vendor")

    @staticmethod
    def get_out_of_stock_cards_list():
        return Card.objects.filter(quantity__lte=settings.OUT_OF_STOCK_THRESHOLD, is_active=True).select_related("vendor")

    @staticmethod
    def get_pending_orders_list():
        return (
            Order.objects.exclude(order_status__in=[Order.OrderStatus.DELIVERED, Order.OrderStatus.FULLY_PAID])
            .select_related("customer", "staff")
            .order_by("-order_date")
        )

    @staticmethod
    def get_pending_bills_list():
        return (
            Bill.objects.filter(Q(payment_status=Bill.PaymentStatus.PENDING) | Q(payment_status=Bill.PaymentStatus.PARTIAL))
            .select_related("order", "order__customer")
            .order_by("-created_at")
        )

    @staticmethod
    def get_pending_printing_jobs_list():
        return (
            PrintingJob.objects.exclude(printing_status=PrintingJob.PrintingStatus.COMPLETED)
            .select_related("order_item__order__customer", "printer", "tracing_studio")
            .order_by("-created_at")
        )

    @staticmethod
    def get_pending_box_jobs_list():
        return (
            BoxOrder.objects.exclude(box_status=BoxOrder.BoxStatus.COMPLETED)
            .select_related("order_item__order__customer", "box_maker")
            .order_by("-created_at")
        )

    @staticmethod
    def get_todays_orders_list():
        today = timezone.now().date()
        return OrderService.get_orders_queryset().select_related("bill").filter(order_date__date=today).order_by("-order_date")


class CardAnalyticsService:
    """Per-card business analytics and summary statistics."""

    @staticmethod
    def get_card_stats(card_id: str, months: int = 6) -> dict:
        """
        Compute sales and revenue stats for a specific card.

        Returns a dictionary with:
        - orders_count
        - units_sold
        - gross_revenue
        - gross_cost
        - gross_profit
        - avg_selling_price
        - avg_discount_per_unit
        - avg_discount_rate
        - first_sold_at
        - last_sold_at
        - distinct_customers
        - returns: {transactions, units_returned}
        - order_status_breakdown: {status: orders}
        - orders: [{order_id, name, quantity}] for this card
        """

        # Base queryset of order items for this card
        order_items_qs = OrderItem.objects.filter(card_id=card_id)

        # Early return when there are no sales yet
        if not order_items_qs.exists():
            # Returns section still reflects any returns that might exist (edge case)
            return_transactions = InventoryTransaction.objects.filter(
                card_id=card_id, transaction_type=InventoryTransaction.TransactionType.RETURN
            ).aggregate(transactions=Count("id"), units=Sum("quantity_changed"))

            return {
                "orders_count": 0,
                "units_sold": 0,
                "gross_revenue": Decimal("0.00"),
                "gross_cost": Decimal("0.00"),
                "gross_profit": Decimal("0.00"),
                "avg_selling_price": None,
                "avg_discount_per_unit": Decimal("0.00"),
                "avg_discount_rate": Decimal("0.00"),
                "first_sold_at": None,
                "last_sold_at": None,
                "distinct_customers": 0,
                "returns": {
                    "transactions": return_transactions.get("transactions") or 0,
                    "units_returned": return_transactions.get("units") or 0,
                },
                "order_status_breakdown": {},
                "orders": [],
            }

        # Subquery to reference the per-item sale cost price captured at the time of sale
        sale_cost_price_sq = Subquery(
            InventoryTransaction.objects.filter(
                order_item_id=OuterRef("pk"), transaction_type=InventoryTransaction.TransactionType.SALE
            )
            .order_by("-created_at")
            .values("cost_price")[:1]
        )

        # Annotate order items with sale-time cost_price for accurate historical costing
        annotated_items = order_items_qs.annotate(sale_cost_price=sale_cost_price_sq)

        # Aggregations for core metrics
        revenue_expr = ExpressionWrapper(
            (F("price_per_item") - F("discount_amount")) * F("quantity"),
            output_field=DecimalField(max_digits=18, decimal_places=PRICE_DECIMAL_PLACES),
        )
        cost_expr = ExpressionWrapper(
            F("quantity") * F("sale_cost_price"),
            output_field=DecimalField(max_digits=18, decimal_places=PRICE_DECIMAL_PLACES),
        )
        discount_total_expr = ExpressionWrapper(
            F("discount_amount") * F("quantity"),
            output_field=DecimalField(max_digits=18, decimal_places=PRICE_DECIMAL_PLACES),
        )

        aggregates = annotated_items.aggregate(
            orders_count=Count("order_id", distinct=True),
            units_sold=Sum("quantity"),
            gross_revenue=Sum(revenue_expr),
            gross_cost=Sum(cost_expr),
            discount_total=Sum(discount_total_expr),
            first_sold_at=Min("created_at"),
            last_sold_at=Max("created_at"),
            distinct_customers=Count("order__customer_id", distinct=True),
        )

        units_sold = aggregates.get("units_sold") or 0
        gross_revenue = aggregates.get("gross_revenue") or Decimal("0.00")
        gross_cost = aggregates.get("gross_cost") or Decimal("0.00")
        discount_total = aggregates.get("discount_total") or Decimal("0.00")

        gross_profit = gross_revenue - gross_cost
        avg_selling_price = (gross_revenue / units_sold) if units_sold else None
        avg_discount_per_unit = (discount_total / units_sold) if units_sold else Decimal("0.00")
        # Weighted average discount rate relative to list price
        price_total_expr = ExpressionWrapper(
            F("price_per_item") * F("quantity"),
            output_field=DecimalField(max_digits=18, decimal_places=PRICE_DECIMAL_PLACES),
        )
        price_total = annotated_items.aggregate(total=Sum(price_total_expr)).get("total") or Decimal("0.00")
        avg_discount_rate = (discount_total / price_total) if price_total > 0 else Decimal("0.00")

        # Returns info (quantity_changed is positive for RETURN)
        return_data = InventoryTransaction.objects.filter(
            card_id=card_id, transaction_type=InventoryTransaction.TransactionType.RETURN
        ).aggregate(transactions=Count("id"), units=Sum("quantity_changed"))

        # Order status breakdown (distinct orders per status)
        status_qs = (
            order_items_qs.values("order__order_status")
            .annotate(order_count=Count("order_id", distinct=True))
            .order_by()
        )
        status_breakdown: dict[str, int] = {}
        for row in status_qs:
            status_breakdown[row["order__order_status"]] = row["order_count"]

        # Orders list: one row per order (name and quantity of this card in that order)
        orders_qs = (
            order_items_qs.values("order_id", "order__name")
            .annotate(quantity=Sum("quantity"))
            .order_by("-order__order_date")
        )
        orders_list = [
            {"order_id": row["order_id"], "name": row["order__name"], "quantity": row["quantity"] or 0}
            for row in orders_qs
        ]

        return {
            "orders_count": aggregates.get("orders_count") or 0,
            "units_sold": units_sold,
            "gross_revenue": gross_revenue,
            "gross_cost": gross_cost,
            "gross_profit": gross_profit,
            "avg_selling_price": avg_selling_price,
            "avg_discount_per_unit": avg_discount_per_unit,
            "avg_discount_rate": avg_discount_rate,
            "first_sold_at": aggregates.get("first_sold_at"),
            "last_sold_at": aggregates.get("last_sold_at"),
            "distinct_customers": aggregates.get("distinct_customers") or 0,
            "returns": {
                "transactions": return_data.get("transactions") or 0,
                "units_returned": return_data.get("units") or 0,
            },
            "order_status_breakdown": status_breakdown,
            "orders": orders_list,
        }
