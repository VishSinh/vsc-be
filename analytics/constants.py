from django.db import models


class AnalyticsType(models.TextChoices):
    YEARLY_PROFIT = "yearly_profit", "Yearly Profit"
    LOW_STOCK_CARDS = "low_stock_cards", "Low Stock Cards"
    OUT_OF_STOCK_CARDS = "out_of_stock_cards", "Out of Stock Cards"
    PENDING_ORDERS = "pending_orders", "Pending Orders"
    PENDING_BILLS = "pending_bills", "Pending Bills"
    PENDING_PRINTING_JOBS = "pending_printing_jobs", "Pending Printing Jobs"
    PENDING_BOX_JOBS = "pending_box_jobs", "Pending Box Jobs"
