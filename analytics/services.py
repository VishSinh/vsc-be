from datetime import date, timedelta
from decimal import Decimal

from dateutil.relativedelta import relativedelta  # type: ignore
from django.conf import settings
from django.db.models import Q
from django.utils import timezone

from inventory.models import Card, InventoryTransaction
from orders.models import Bill, Order
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
        return (
            Order.objects.filter(order_date__date=today)
            .select_related("customer", "staff")
            .order_by("-order_date")
        )
