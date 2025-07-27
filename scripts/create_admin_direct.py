#!/usr/bin/env python3
"""
Direct database injection script to create an admin user.
This script directly inserts into the database without using Django ORM.
"""

import hashlib
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path

import psycopg2
from passlib.context import CryptContext

# Database configuration
DB_CONFIG = {"host": "localhost", "port": 5432, "database": "vsc", "user": "vish", "password": "vish123"}


def hash_password(password):
    """Hash password using bcrypt-like approach"""
    # For simplicity, using SHA256 with salt
    salt = "vsc_salt_2024"
    salted = password + salt
    return hashlib.sha256(salted.encode()).hexdigest()


def create_admin_direct(username="admin", email="admin@example.com", password="admin123", phone="1234567890", first_name="Admin", last_name="User"):
    """Create admin user directly in database"""

    try:
        # Connect to database
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()

        # Generate UUID for the user
        user_id = str(uuid.uuid4())

        # Hash the password
        hashed_password = CryptContext(schemes=["bcrypt"], deprecated="auto").hash(password)

        # Current timestamp
        now = datetime.now(timezone.utc)

        # Check if user already exists
        cursor.execute("SELECT id FROM staff WHERE username = %s", (username,))
        existing_user = cursor.fetchone()

        if existing_user:
            print(f"User '{username}' already exists!")
            return False

        # Insert the admin user
        insert_query = """
        INSERT INTO staff (
            id, username, password, email, phone, first_name, last_name,
            role, is_staff, is_superuser, is_active, date_joined, created_at, updated_at
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
        )
        """

        cursor.execute(
            insert_query,
            (
                user_id,
                username,
                hashed_password,
                email,
                phone,
                first_name,
                last_name,
                "ADMIN",  # role
                True,  # is_staff
                True,  # is_superuser
                True,  # is_active
                now,  # date_joined
                now,  # created_at
                now,  # updated_at
            ),
        )

        conn.commit()
        print(f"✅ Admin user '{username}' created successfully!")
        print(f"   ID: {user_id}")
        print(f"   Email: {email}")
        print(f"   Role: ADMIN")
        print(f"   Password: {password}")

        return True

    except psycopg2.Error as e:
        print(f"❌ Database error: {e}")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False
    finally:
        if "conn" in locals():
            conn.close()


def main():
    """Main function"""
    import argparse

    parser = argparse.ArgumentParser(description="Create admin user directly in database")
    parser.add_argument("--username", default="admin", help="Username")
    parser.add_argument("--email", default="admin@example.com", help="Email")
    parser.add_argument("--password", default="admin123", help="Password")
    parser.add_argument("--phone", default="1234567890", help="Phone")
    parser.add_argument("--first-name", default="Admin", help="First name")
    parser.add_argument("--last-name", default="User", help="Last name")

    args = parser.parse_args()

    print("🚀 Creating admin user directly in database...")
    print(f"   Database: {DB_CONFIG['database']}")
    print(f"   Host: {DB_CONFIG['host']}:{DB_CONFIG['port']}")
    print()

    success = create_admin_direct(
        username=args.username, email=args.email, password=args.password, phone=args.phone, first_name=args.first_name, last_name=args.last_name
    )

    if success:
        print("\n✅ Admin user created successfully!")
        print("   You can now login with the credentials above.")
    else:
        print("\n❌ Failed to create admin user.")
        exit(1)


if __name__ == "__main__":
    main()
