from django.db import transaction
from django.utils import timezone

from accounts.models import Staff
from core.exceptions import ResourceNotFound, Unauthorized
from core.helpers.security import Security


class StaffService:
    @staticmethod
    @transaction.atomic
    def create_staff(name, phone, password, role):
        """
        Creates a new staff member with hashed password.
        """
        # Check if phone already exists
        if Staff.objects.filter(phone=phone).exists():
            raise Unauthorized("Phone number already registered")

        # Hash the password
        hashed_password = Security.get_password_hash(password)

        # Create staff member
        staff = Staff.objects.create(name=name, phone=phone, password=hashed_password, role=role)

        return staff

    @staticmethod
    def authenticate_staff_and_get_token(staff, password):
        """
        Authenticates a staff member and returns login data.
        """
        # Verify password
        if not Security.verify_password(password, staff.password):
            raise Unauthorized("Invalid phone or password")

        # Check if staff is active
        if not staff.is_active:
            raise Unauthorized("Account is deactivated")

        # Update last login
        staff.last_login = timezone.now()
        staff.save(update_fields=["last_login"])

        # Generate token
        token = Security.create_token({"staff_id": str(staff.id), "role": staff.role})

        return token

    @staticmethod
    def get_staff_by_phone(phone):
        """
        Retrieves a staff member by phone.
        """
        staff = Staff.objects.filter(phone=phone, is_active=True).first()
        if not staff:
            raise ResourceNotFound("Staff member not found")

        return staff

    @staticmethod
    def get_staff_by_id(staff_id):
        """
        Retrieves a staff member by ID.
        """
        staff = Staff.objects.filter(id=staff_id, is_active=True).first()
        if not staff:
            raise ResourceNotFound("Staff member not found")
        return staff
