from prometheus_client import Counter, Gauge


# Application traffic
REQUEST_COUNTER = Counter(
    "app_requests_total",
    "Total HTTP requests processed by the application",
    labelnames=("method", "path", "status"),
)

REQUEST_INFLIGHT = Gauge(
    "app_requests_inflight",
    "Number of in-flight HTTP requests",
)


# Business metrics
ORDERS_CREATED = Counter(
    "business_orders_created_total",
    "Total number of orders created",
)

ORDER_ITEMS_CREATED = Counter(
    "business_order_items_created_total",
    "Total number of order items created",
)

SERVICE_ITEMS_CREATED = Counter(
    "business_service_items_created_total",
    "Total number of service items created",
)

PENDING_ORDERS = Gauge(
    "business_pending_orders",
    "Current count of pending orders (not delivered or fully paid)",
)

LOW_STOCK_ITEMS = Gauge(
    "business_low_stock_items",
    "Current count of low stock items",
)

OUT_OF_STOCK_ITEMS = Gauge(
    "business_out_of_stock_items",
    "Current count of out of stock items",
)


