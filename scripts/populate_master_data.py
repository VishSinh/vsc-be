#!/usr/bin/env python3
"""
Master data population script for VSC card trading system.
Populates all major tables with realistic test data, exactly mimicking the actual code.
"""

import os
import sys
import time
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

import psycopg2
from passlib.context import CryptContext

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

# Database configuration
DB_CONFIG = {"host": "localhost", "port": 5432, "database": "vsc", "user": "vish", "password": "vish123"}

# Data constants - exactly matching model choices
STAFF_DATA = [
    {"username": "admin", "name": "Admin User", "phone": "9876543210", "role": "ADMIN"},
    {"username": "manager", "name": "Manager User", "phone": "9876543211", "role": "MANAGER"},
    {"username": "sales1", "name": "Sales User 1", "phone": "9876543212", "role": "SALES"},
    {"username": "sales2", "name": "Sales User 2", "phone": "9876543213", "role": "SALES"},
]

VENDOR_DATA = [
    {"name": "CardCraft Supplies", "phone": "8765432101"},
    {"name": "Premium Cards Co", "phone": "8765432102"},
    {"name": "Artistic Cards Ltd", "phone": "8765432103"},
    {"name": "Quality Card Makers", "phone": "8765432104"},
]

CARD_DATA = [
    {"sell_price": "25.00", "cost_price": "15.00", "max_discount": "5.00", "quantity": 50},
    {"sell_price": "30.00", "cost_price": "18.00", "max_discount": "8.00", "quantity": 30},
    {"sell_price": "20.00", "cost_price": "12.00", "max_discount": "3.00", "quantity": 75},
    {"sell_price": "35.00", "cost_price": "22.00", "max_discount": "10.00", "quantity": 25},
    {"sell_price": "40.00", "cost_price": "25.00", "max_discount": "12.00", "quantity": 20},
]

CUSTOMER_DATA = [
    {"name": "John Smith", "phone": "7654321091"},
    {"name": "Sarah Johnson", "phone": "7654321092"},
    {"name": "Mike Davis", "phone": "7654321093"},
    {"name": "Emily Wilson", "phone": "7654321094"},
    {"name": "David Brown", "phone": "7654321095"},
]

PRODUCTION_DATA = [
    {"name": "PrintPro Services", "phone": "6543210981"},
    {"name": "Tracing Studio Plus", "phone": "6543210982"},
    {"name": "BoxCraft Makers", "phone": "6543210983"},
]


class MasterDataPopulator:
    def __init__(self):
        self.conn = None
        self.cursor = None
        self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        self.created_data = {}

    def connect(self):
        """Connect to database"""
        try:
            self.conn = psycopg2.connect(**DB_CONFIG)
            self.cursor = self.conn.cursor()
            print("✅ Connected to database successfully")
        except Exception as e:
            print(f"❌ Database connection failed: {e}")
            sys.exit(1)

    def disconnect(self):
        """Disconnect from database"""
        if self.conn:
            self.conn.close()
            print("✅ Disconnected from database")

    def generate_unique_barcode(self, prefix: str = "CARD") -> str:
        """Generate unique barcode exactly like the original code"""
        max_attempts = 10
        for _ in range(max_attempts):
            timestamp = int(time.time() * 1000)
            random_suffix = str(uuid.uuid4())[:8]
            barcode = f"{prefix}_{timestamp}_{random_suffix}"

            # Check uniqueness
            self.cursor.execute("SELECT id FROM cards WHERE barcode = %s", (barcode,))
            if not self.cursor.fetchone():
                return barcode

        raise Exception("Unable to generate unique barcode after multiple attempts")

    def generate_perceptual_hash(self, barcode: str) -> str:
        """Generate perceptual hash exactly like the original code"""
        # Using a simple hash for demo purposes - in real code this would process an image
        return f"hash_{barcode}_{int(time.time())}"

    def create_staff(self):
        """Create staff members"""
        print("\n👥 Creating staff members...")

        for staff_data in STAFF_DATA:
            staff_id = str(uuid.uuid4())
            hashed_password = self.pwd_context.hash("password123")
            now = datetime.now(timezone.utc)

            self.cursor.execute(
                """
                INSERT INTO staff (
                    id, username, password, email, phone, name, first_name, last_name,
                    role, is_staff, is_superuser, is_active, date_joined, created_at, updated_at
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                )
            """,
                (
                    staff_id,
                    staff_data["username"],
                    hashed_password,
                    f"{staff_data['username']}@example.com",
                    staff_data["phone"],
                    staff_data["name"],
                    staff_data["name"],
                    "",
                    staff_data["role"],
                    True,
                    True,
                    True,
                    now,
                    now,
                    now,
                ),
            )

            self.created_data.setdefault("staff", []).append({"id": staff_id, "username": staff_data["username"], "role": staff_data["role"]})
            print(f"   ✅ Created {staff_data['username']} ({staff_data['role']})")

    def create_vendors(self):
        """Create vendors"""
        print("\n🏢 Creating vendors...")

        for vendor_data in VENDOR_DATA:
            vendor_id = str(uuid.uuid4())
            now = datetime.now(timezone.utc)

            self.cursor.execute(
                """
                INSERT INTO vendors (id, name, phone, is_active, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s)
            """,
                (vendor_id, vendor_data["name"], vendor_data["phone"], True, now, now),
            )

            self.created_data.setdefault("vendors", []).append({"id": vendor_id, "name": vendor_data["name"]})
            print(f"   ✅ Created {vendor_data['name']}")

    def create_cards(self):
        """Create cards with inventory"""
        print("\n🃏 Creating cards...")

        for i, card_data in enumerate(CARD_DATA):
            card_id = str(uuid.uuid4())
            vendor_id = self.created_data["vendors"][i % len(self.created_data["vendors"])]["id"]
            barcode = self.generate_unique_barcode()
            perceptual_hash = self.generate_perceptual_hash(barcode)
            now = datetime.now(timezone.utc)

            self.cursor.execute(
                """
                INSERT INTO cards (
                    id, vendor_id, barcode, sell_price, cost_price, max_discount, quantity,
                    image, perceptual_hash, is_active, created_at, updated_at
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                )
            """,
                (
                    card_id,
                    vendor_id,
                    barcode,
                    card_data["sell_price"],
                    card_data["cost_price"],
                    card_data["max_discount"],
                    card_data["quantity"],
                    f"https://example.com/cards/{barcode}.jpg",
                    perceptual_hash,
                    True,
                    now,
                    now,
                ),
            )

            self.created_data.setdefault("cards", []).append(
                {"id": card_id, "barcode": barcode, "quantity": card_data["quantity"], "sell_price": card_data["sell_price"]}
            )
            print(f"   ✅ Created {barcode} (Qty: {card_data['quantity']})")

    def create_customers(self):
        """Create customers"""
        print("\n👤 Creating customers...")

        for customer_data in CUSTOMER_DATA:
            customer_id = str(uuid.uuid4())
            now = datetime.now(timezone.utc)

            self.cursor.execute(
                """
                INSERT INTO customers (id, name, phone, is_active, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s)
            """,
                (customer_id, customer_data["name"], customer_data["phone"], True, now, now),
            )

            self.created_data.setdefault("customers", []).append({"id": customer_id, "name": customer_data["name"]})
            print(f"   ✅ Created {customer_data['name']}")

    def create_production_services(self):
        """Create production service providers"""
        print("\n🏭 Creating production services...")

        # Create printers
        for i, data in enumerate(PRODUCTION_DATA):
            printer_id = str(uuid.uuid4())
            now = datetime.now(timezone.utc)

            self.cursor.execute(
                """
                INSERT INTO printers (id, name, phone, is_active, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s)
            """,
                (printer_id, f"{data['name']} - Printer", data["phone"], True, now, now),
            )

            self.created_data.setdefault("printers", []).append({"id": printer_id})
            print(f"   ✅ Created printer: {data['name']} - Printer")

        # Create tracing studios
        for i, data in enumerate(PRODUCTION_DATA):
            studio_id = str(uuid.uuid4())
            now = datetime.now(timezone.utc)

            self.cursor.execute(
                """
                INSERT INTO tracing_studios (id, name, phone, is_active, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s)
            """,
                (studio_id, f"{data['name']} - Tracing", data["phone"], True, now, now),
            )

            self.created_data.setdefault("tracing_studios", []).append({"id": studio_id})
            print(f"   ✅ Created tracing studio: {data['name']} - Tracing")

        # Create box makers
        for i, data in enumerate(PRODUCTION_DATA):
            box_maker_id = str(uuid.uuid4())
            now = datetime.now(timezone.utc)

            self.cursor.execute(
                """
                INSERT INTO box_makers (id, name, phone, is_active, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s)
            """,
                (box_maker_id, f"{data['name']} - Box", data["phone"], True, now, now),
            )

            self.created_data.setdefault("box_makers", []).append({"id": box_maker_id})
            print(f"   ✅ Created box maker: {data['name']} - Box")

    def create_orders_and_items(self):
        """Create orders with order items"""
        print("\n📦 Creating orders and order items...")

        for i in range(3):  # Create 3 orders
            # Create order
            order_id = str(uuid.uuid4())
            customer_id = self.created_data["customers"][i % len(self.created_data["customers"])]["id"]
            staff_id = self.created_data["staff"][i % len(self.created_data["staff"])]["id"]
            now = datetime.now(timezone.utc)
            delivery_date = now + timedelta(days=7)

            self.cursor.execute(
                """
                INSERT INTO orders (
                    id, customer_id, staff_id, order_date, delivery_date, order_status,
                    special_instruction, created_at, updated_at
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s
                )
            """,
                (order_id, customer_id, staff_id, now, delivery_date, "CONFIRMED", f"Special instruction for order {i+1}", now, now),
            )

            # Create order items for this order
            for j in range(2):  # 2 items per order
                card = self.created_data["cards"][(i + j) % len(self.created_data["cards"])]
                order_item_id = str(uuid.uuid4())
                quantity = 2 + j
                discount_amount = Decimal("2.00") if j == 0 else Decimal("0.00")
                price_per_item = Decimal(card["sell_price"]) - discount_amount

                self.cursor.execute(
                    """
                    INSERT INTO order_items (
                        id, order_id, card_id, quantity, price_per_item, discount_amount,
                        requires_box, requires_printing, created_at, updated_at
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                    )
                """,
                    (order_item_id, order_id, card["id"], quantity, price_per_item, discount_amount, j == 0, j == 1, now, now),
                )

                # Create production services for some items
                if j == 0:  # First item gets box
                    box_order_id = str(uuid.uuid4())
                    box_maker_id = self.created_data["box_makers"][0]["id"]

                    self.cursor.execute(
                        """
                        INSERT INTO box_orders (
                            id, order_item_id, box_maker_id, box_type, box_quantity,
                            total_box_cost, box_status, estimated_completion, created_at, updated_at
                        ) VALUES (
                            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                        )
                    """,
                        (
                            box_order_id,
                            order_item_id,
                            box_maker_id,
                            "FOLDING",
                            quantity,
                            Decimal("15.00"),
                            "PENDING",
                            now + timedelta(days=3),
                            now,
                            now,
                        ),
                    )

                if j == 1:  # Second item gets printing
                    printing_job_id = str(uuid.uuid4())
                    printer_id = self.created_data["printers"][0]["id"]
                    tracing_studio_id = self.created_data["tracing_studios"][0]["id"]

                    self.cursor.execute(
                        """
                        INSERT INTO printing_jobs (
                            id, order_item_id, printer_id, tracing_studio_id, print_quantity,
                            total_printing_cost, printing_status, estimated_completion, created_at, updated_at
                        ) VALUES (
                            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                        )
                    """,
                        (
                            printing_job_id,
                            order_item_id,
                            printer_id,
                            tracing_studio_id,
                            quantity,
                            Decimal("20.00"),
                            "PENDING",
                            now + timedelta(days=2),
                            now,
                            now,
                        ),
                    )

            print(f"   ✅ Created order {i+1} with 2 items")

    def create_bills_and_payments(self):
        """Create bills and payments for orders"""
        print("\n💰 Creating bills and payments...")

        # Get all orders
        self.cursor.execute("SELECT id FROM orders")
        orders = self.cursor.fetchall()

        for order_id in orders:
            order_id = order_id[0]

            # Create bill
            bill_id = str(uuid.uuid4())
            now = datetime.now(timezone.utc)

            self.cursor.execute(
                """
                INSERT INTO bills (id, order_id, tax_percentage, payment_status, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s)
            """,
                (bill_id, order_id, Decimal("5.00"), "PAID", now, now),
            )

            # Create payment
            payment_id = str(uuid.uuid4())

            self.cursor.execute(
                """
                INSERT INTO payments (
                    id, bill_id, amount, payment_mode, transaction_ref, notes, created_at
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s
                )
            """,
                (payment_id, bill_id, Decimal("100.00"), "CASH", f"TXN{payment_id[:8]}", "Payment for order", now),
            )

            print(f"   ✅ Created bill and payment for order {order_id[:8]}")

    def create_inventory_transactions(self):
        """Create inventory transactions for stock movements"""
        print("\n📊 Creating inventory transactions...")

        # Get all cards
        self.cursor.execute("SELECT id, quantity FROM cards")
        cards = self.cursor.fetchall()

        for card_id, current_quantity in cards:
            # Create initial purchase transaction
            transaction_id = str(uuid.uuid4())
            staff_id = self.created_data["staff"][0]["id"]  # Use admin
            now = datetime.now(timezone.utc)

            self.cursor.execute(
                """
                INSERT INTO inventory_transactions (
                    id, card_id, staff_id, transaction_type, quantity_changed,
                    cost_price, notes, created_at
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s
                )
            """,
                (transaction_id, card_id, staff_id, "PURCHASE", current_quantity, Decimal("15.00"), "Initial stock purchase", now),
            )

            print(f"   ✅ Created purchase transaction for card {card_id[:8]}")

    def create_audit_logs(self):
        """Create sample audit logs"""
        print("\n📝 Creating audit logs...")

        # Get some staff and cards for audit logs
        self.cursor.execute("SELECT id FROM staff LIMIT 2")
        staff_ids = [row[0] for row in self.cursor.fetchall()]

        self.cursor.execute("SELECT id FROM cards LIMIT 3")
        card_ids = [row[0] for row in self.cursor.fetchall()]

        for i, staff_id in enumerate(staff_ids):
            for j, card_id in enumerate(card_ids):
                audit_log_id = str(uuid.uuid4())
                now = datetime.now(timezone.utc)

                self.cursor.execute(
                    """
                    INSERT INTO audit_logs (
                        id, staff_id, table_name, record_id, action, old_values, new_values, created_at
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s
                    )
                """,
                    (audit_log_id, staff_id, "cards", card_id, "CREATE", "", f'{{"barcode": "CARD{i+j}"}}', now),
                )

            print(f"   ✅ Created audit logs for staff {staff_id[:8]}")

    def populate_all(self):
        """Populate all tables with test data"""
        print("🚀 Starting master data population...")
        print(f"   Database: {DB_CONFIG['database']}")
        print(f"   Host: {DB_CONFIG['host']}:{DB_CONFIG['port']}")

        try:
            self.connect()

            # Create data in dependency order
            self.create_staff()
            self.create_vendors()
            self.create_cards()
            self.create_customers()
            self.create_production_services()
            self.create_orders_and_items()
            self.create_bills_and_payments()
            self.create_inventory_transactions()
            self.create_audit_logs()

            # Commit all changes
            self.conn.commit()

            print("\n✅ Master data population completed successfully!")
            print(f"   Created {len(self.created_data.get('staff', []))} staff members")
            print(f"   Created {len(self.created_data.get('vendors', []))} vendors")
            print(f"   Created {len(self.created_data.get('cards', []))} cards")
            print(f"   Created {len(self.created_data.get('customers', []))} customers")
            print(f"   Created orders with production services")
            print(f"   Created bills and payments")
            print(f"   Created inventory transactions")
            print(f"   Created audit logs")

            print("\n🔑 Login Credentials:")
            for staff in self.created_data.get("staff", []):
                print(f"   {staff['username']}: password123 ({staff['role']})")

        except Exception as e:
            print(f"\n❌ Error during population: {e}")
            if self.conn:
                self.conn.rollback()
            sys.exit(1)
        finally:
            self.disconnect()


def main():
    """Main function"""
    import argparse

    parser = argparse.ArgumentParser(description="Populate master data for VSC system")
    parser.add_argument("--clear", action="store_true", help="Clear existing data before populating")

    args = parser.parse_args()

    if args.clear:
        print("⚠️  Warning: This will clear all existing data!")
        response = input("Are you sure? (y/N): ")
        if response.lower() != "y":
            print("❌ Operation cancelled")
            sys.exit(0)

    populator = MasterDataPopulator()
    populator.populate_all()


if __name__ == "__main__":
    main()
