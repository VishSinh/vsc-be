from django.utils import timezone
from rest_framework.views import APIView

from analytics.constants import AnalyticsType
from analytics.serializers import DetailedAnalyticsParams
from analytics.services import AnalyticsService
from core.decorators import forge
from core.utils import model_unwrap


class DashboardView(APIView):
    @forge
    def get(self, request):
        today = timezone.now().date()

        low_stock_items = AnalyticsService.get_low_stock_items()
        out_of_stock_items = AnalyticsService.get_out_of_stock_items()
        total_orders = AnalyticsService.get_total_orders_current_month()
        monthly_order_change = AnalyticsService.get_monthly_order_change()
        pending_orders = AnalyticsService.get_pending_orders()
        todays_orders = AnalyticsService.get_todays_orders(today)
        pending_bills_count = AnalyticsService.get_pending_bills_count()
        profit_analysis = AnalyticsService.get_monthly_profit_analysis()
        pending_printing, pending_boxing = AnalyticsService.get_pending_production_counts()

        return {
            "low_stock_items": low_stock_items,
            "out_of_stock_items": out_of_stock_items,
            "total_orders_current_month": total_orders,
            "monthly_order_change_percentage": monthly_order_change,
            "pending_orders": pending_orders,
            "todays_orders": todays_orders,
            "pending_bills": pending_bills_count,
            "monthly_profit": f"{profit_analysis['monthly_profit']:.2f}",
            "orders_pending_expense_logging": profit_analysis["orders_pending_expense_logging"],
            "pending_printing_jobs": pending_printing,
            "pending_box_jobs": pending_boxing,
        }


class DetailedAnalyticsView(APIView):
    @forge
    def get(self, request):
        params = DetailedAnalyticsParams.validate_params(request)
        analytics_type = params.get_value("type")

        data_fetchers = {
            AnalyticsType.YEARLY_PROFIT: AnalyticsService.get_yearly_profit_analysis,
            AnalyticsType.LOW_STOCK_CARDS: AnalyticsService.get_low_stock_cards_list,
            AnalyticsType.OUT_OF_STOCK_CARDS: AnalyticsService.get_out_of_stock_cards_list,
            AnalyticsType.PENDING_ORDERS: AnalyticsService.get_pending_orders_list,
            AnalyticsType.PENDING_BILLS: AnalyticsService.get_pending_bills_list,
            AnalyticsType.PENDING_PRINTING_JOBS: AnalyticsService.get_pending_printing_jobs_list,
            AnalyticsType.PENDING_BOX_JOBS: AnalyticsService.get_pending_box_jobs_list,
            AnalyticsType.TODAYS_ORDERS: AnalyticsService.get_todays_orders_list,
        }

        fetcher = data_fetchers.get(analytics_type)

        if fetcher is None:
            # This case should ideally not be hit due to the serializer's validation,
            # but we handle it to satisfy the linter and for extra safety.
            return

        # For methods that return lists of model objects, we serialize them.
        # For yearly_profit, the data is already a list of dicts.
        if analytics_type == AnalyticsType.YEARLY_PROFIT:
            data = fetcher()
            return data
        elif analytics_type == AnalyticsType.TODAYS_ORDERS:
            # Custom weaving to include nested order_items, printing_jobs, box_orders, service_items, and bill_id
            queryset = fetcher()
            results = []
            for order in queryset:
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
                bill = getattr(order, "bill", None)
                order_data["bill_id"] = model_unwrap(bill).get("id") if bill else None
                results.append(order_data)
            return results
        else:
            queryset = fetcher()
            return model_unwrap(queryset)
