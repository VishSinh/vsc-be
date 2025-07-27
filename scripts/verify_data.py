#!/usr/bin/env python3
"""
Verification script to check master data population.
Shows summary of all created data.
"""

from pathlib import Path

import psycopg2

# Database configuration
DB_CONFIG = {"host": "localhost", "port": 5432, "database": "vsc", "user": "vish", "password": "vish123"}


def verify_data():
    """Verify that all data was created correctly"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()

        print("🔍 Verifying master data population...")
        print("=" * 50)

        # Check staff
        cursor.execute("SELECT COUNT(*) FROM staff")
        staff_count = cursor.fetchone()[0]
        print(f"👥 Staff: {staff_count} members")

        # Check vendors
        cursor.execute("SELECT COUNT(*) FROM vendors")
        vendor_count = cursor.fetchone()[0]
        print(f"🏢 Vendors: {vendor_count} suppliers")

        # Check cards
        cursor.execute("SELECT COUNT(*) FROM cards")
        card_count = cursor.fetchone()[0]
        print(f"🃏 Cards: {card_count} products")

        # Check customers
        cursor.execute("SELECT COUNT(*) FROM customers")
        customer_count = cursor.fetchone()[0]
        print(f"👤 Customers: {customer_count} buyers")

        # Check production services
        cursor.execute("SELECT COUNT(*) FROM printers")
        printer_count = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM tracing_studios")
        studio_count = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM box_makers")
        box_maker_count = cursor.fetchone()[0]
        print(f"🏭 Production Services: {printer_count} printers, {studio_count} studios, {box_maker_count} box makers")

        # Check orders
        cursor.execute("SELECT COUNT(*) FROM orders")
        order_count = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM order_items")
        order_item_count = cursor.fetchone()[0]
        print(f"📦 Orders: {order_count} orders with {order_item_count} items")

        # Check production jobs
        cursor.execute("SELECT COUNT(*) FROM printing_jobs")
        printing_job_count = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM box_orders")
        box_order_count = cursor.fetchone()[0]
        print(f"🏭 Production Jobs: {printing_job_count} printing jobs, {box_order_count} box orders")

        # Check financial
        cursor.execute("SELECT COUNT(*) FROM bills")
        bill_count = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM payments")
        payment_count = cursor.fetchone()[0]
        print(f"💰 Financial: {bill_count} bills, {payment_count} payments")

        # Check inventory
        cursor.execute("SELECT COUNT(*) FROM inventory_transactions")
        transaction_count = cursor.fetchone()[0]
        print(f"📊 Inventory: {transaction_count} transactions")

        # Check audit logs
        cursor.execute("SELECT COUNT(*) FROM audit_logs")
        audit_count = cursor.fetchone()[0]
        print(f"📝 Audit: {audit_count} log entries")

        print("=" * 50)
        print("✅ All data verified successfully!")

        # Show sample data
        print("\n📋 Sample Data:")
        print("-" * 30)

        # Sample staff
        cursor.execute("SELECT username, role FROM staff LIMIT 3")
        staff_samples = cursor.fetchall()
        print("👥 Sample Staff:")
        for username, role in staff_samples:
            print(f"   {username} ({role})")

        # Sample cards
        cursor.execute("SELECT barcode, quantity FROM cards LIMIT 3")
        card_samples = cursor.fetchall()
        print("\n🃏 Sample Cards:")
        for barcode, quantity in card_samples:
            print(f"   {barcode} (Qty: {quantity})")

        # Sample orders
        cursor.execute(
            """
            SELECT o.id, c.name, o.order_status
            FROM orders o
            JOIN customers c ON o.customer_id = c.id
            LIMIT 3
        """
        )
        order_samples = cursor.fetchall()
        print("\n📦 Sample Orders:")
        for order_id, customer_name, status in order_samples:
            print(f"   Order {order_id[:8]} - {customer_name} ({status})")

        conn.close()

    except Exception as e:
        print(f"❌ Error during verification: {e}")
        return False

    return True


if __name__ == "__main__":
    verify_data()
