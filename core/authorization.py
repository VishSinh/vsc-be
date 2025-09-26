from functools import wraps
from typing import Callable, List, Optional, Union

from django.core.exceptions import PermissionDenied
from django.http import HttpRequest
from rest_framework import status
from rest_framework.permissions import BasePermission
from rest_framework.response import Response

from accounts.models import Staff
from core.exceptions import Unauthorized
from core.helpers.api_response import APIResponse


class Permission:
    """Permission constants for fine-grained access control"""

    # Account Management
    ACCOUNT_CREATE = "account.create"
    ACCOUNT_READ = "account.read"
    ACCOUNT_UPDATE = "account.update"
    ACCOUNT_DELETE = "account.delete"
    ACCOUNT_LIST = "account.list"

    # Inventory Management
    INVENTORY_CREATE = "inventory.create"
    INVENTORY_READ = "inventory.read"
    INVENTORY_UPDATE = "inventory.update"
    INVENTORY_DELETE = "inventory.delete"
    INVENTORY_LIST = "inventory.list"
    INVENTORY_TRANSACTION = "inventory.transaction"

    # Order Management
    ORDER_CREATE = "order.create"
    ORDER_READ = "order.read"
    ORDER_UPDATE = "order.update"
    ORDER_DELETE = "order.delete"
    ORDER_LIST = "order.list"
    ORDER_APPROVE = "order.approve"
    ORDER_CANCEL = "order.cancel"

    # Production Management
    PRODUCTION_CREATE = "production.create"
    PRODUCTION_READ = "production.read"
    PRODUCTION_UPDATE = "production.update"
    PRODUCTION_DELETE = "production.delete"
    PRODUCTION_LIST = "production.list"

    # Financial Management
    BILL_CREATE = "bill.create"
    BILL_READ = "bill.read"
    BILL_UPDATE = "bill.update"
    BILL_DELETE = "bill.delete"
    BILL_LIST = "bill.list"
    PAYMENT_PROCESS = "payment.process"
    PAYMENT_REFUND = "payment.refund"

    # Audit Management
    AUDIT_READ = "audit.read"
    AUDIT_EXPORT = "audit.export"

    # Vendor Management
    VENDOR_CREATE = "vendor.create"
    VENDOR_READ = "vendor.read"
    VENDOR_UPDATE = "vendor.update"
    VENDOR_DELETE = "vendor.delete"
    VENDOR_LIST = "vendor.list"

    # Card Management
    CARD_CREATE = "card.create"
    CARD_READ = "card.read"
    CARD_PURCHASE = "card.purchase"
    CARD_UPDATE = "card.update"
    CARD_DELETE = "card.delete"
    CARD_LIST = "card.list"

    # Customer Management
    CUSTOMER_CREATE = "customer.create"
    CUSTOMER_READ = "customer.read"
    CUSTOMER_UPDATE = "customer.update"
    CUSTOMER_DELETE = "customer.delete"
    CUSTOMER_LIST = "customer.list"

    # Dashboard Management
    DASHBOARD_READ = "dashboard.read"

    # System Management
    SYSTEM_CONFIG = "system.config"
    SYSTEM_BACKUP = "system.backup"
    SYSTEM_RESTORE = "system.restore"


class RolePermissions:
    ADMIN_PERMISSIONS = [value for name, value in Permission.__dict__.items() if not name.startswith("__") and not callable(value)]

    MANAGER_PERMISSIONS = [
        # Management level access
        Permission.ACCOUNT_READ,
        Permission.ACCOUNT_UPDATE,
        Permission.ACCOUNT_LIST,
        Permission.INVENTORY_CREATE,
        Permission.INVENTORY_READ,
        Permission.INVENTORY_UPDATE,
        Permission.INVENTORY_LIST,
        Permission.INVENTORY_TRANSACTION,
        Permission.ORDER_CREATE,
        Permission.ORDER_READ,
        Permission.ORDER_UPDATE,
        Permission.ORDER_LIST,
        Permission.ORDER_APPROVE,
        Permission.ORDER_CANCEL,
        Permission.PRODUCTION_CREATE,
        Permission.PRODUCTION_READ,
        Permission.PRODUCTION_UPDATE,
        Permission.PRODUCTION_LIST,
        Permission.BILL_CREATE,
        Permission.BILL_READ,
        Permission.BILL_UPDATE,
        Permission.BILL_LIST,
        Permission.PAYMENT_PROCESS,
        Permission.AUDIT_READ,
    ]

    SALES_PERMISSIONS = [
        # Basic operational access
        Permission.ACCOUNT_READ,
        Permission.ACCOUNT_LIST,
        Permission.INVENTORY_READ,
        Permission.INVENTORY_LIST,
        Permission.INVENTORY_TRANSACTION,
        Permission.ORDER_CREATE,
        Permission.ORDER_READ,
        Permission.ORDER_LIST,
        Permission.PRODUCTION_READ,
        Permission.PRODUCTION_LIST,
        Permission.BILL_READ,
        Permission.BILL_LIST,
    ]


class AuthorizationService:
    """Service for handling authorization logic"""

    @staticmethod
    def get_user_permissions(staff: Staff) -> List[str]:
        """Get permissions for a specific user"""
        if staff.role == Staff.Role.ADMIN:
            return RolePermissions.ADMIN_PERMISSIONS
        elif staff.role == Staff.Role.MANAGER:
            return RolePermissions.MANAGER_PERMISSIONS
        elif staff.role == Staff.Role.SALES:
            return RolePermissions.SALES_PERMISSIONS
        return []

    @staticmethod
    def has_permission(staff: Staff, permission: str) -> bool:
        """Check if user has specific permission"""
        user_permissions = AuthorizationService.get_user_permissions(staff)
        return permission in user_permissions

    @staticmethod
    def has_any_permission(staff: Staff, permissions: List[str]) -> bool:
        """Check if user has any of the specified permissions"""
        user_permissions = AuthorizationService.get_user_permissions(staff)
        return any(permission in user_permissions for permission in permissions)

    @staticmethod
    def has_all_permissions(staff: Staff, permissions: List[str]) -> bool:
        """Check if user has all of the specified permissions"""
        user_permissions = AuthorizationService.get_user_permissions(staff)
        return all(permission in user_permissions for permission in permissions)


class PermissionMixin:
    """Mixin for adding permission checking to views"""

    permission_required: Optional[Union[str, List[str]]] = None
    permission_any: Optional[List[str]] = None
    permission_all: Optional[List[str]] = None

    def check_permissions(self, request: HttpRequest) -> bool:
        """Check if user has required permissions"""
        if not request.staff.is_authenticated:
            return False

        # Check single permission
        if self.permission_required:
            if isinstance(self.permission_required, str):
                return AuthorizationService.has_permission(request.staff, self.permission_required)
            else:
                return AuthorizationService.has_all_permissions(request.staff, self.permission_required)

        # Check any permission
        if self.permission_any:
            return AuthorizationService.has_any_permission(request.staff, self.permission_any)

        # Check all permissions
        if self.permission_all:
            return AuthorizationService.has_all_permissions(request.staff, self.permission_all)

        return True


class DRFPermission(BasePermission):
    """Django REST Framework permission class"""

    def __init__(self, permission_required: Optional[Union[str, List[str]]] = None):
        self.permission_required = permission_required

    def has_permission(self, request, view):
        if not request.staff.is_authenticated:
            return False

        if not self.permission_required:
            return True

        if isinstance(self.permission_required, str):
            return AuthorizationService.has_permission(request.staff, self.permission_required)
        else:
            return AuthorizationService.has_all_permissions(request.staff, self.permission_required)


def require_permission(permission: Union[str, List[str]]):
    """Decorator for requiring specific permissions"""

    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Extract request from args (assuming it's the first argument after self)
            request = args[1] if len(args) > 1 else None

            if not request or not hasattr(request, "staff"):
                raise PermissionDenied("No user context available")

            if not request.is_authenticated:
                return APIResponse(
                    success=False,
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    error=Unauthorized("Authentication required"),
                ).response()

            if isinstance(permission, str):
                has_perm = AuthorizationService.has_permission(request.staff, permission)
            else:
                has_perm = AuthorizationService.has_all_permissions(request.staff, permission)

            if not has_perm:
                return APIResponse(
                    success=False,
                    status_code=status.HTTP_403_FORBIDDEN,
                    error=PermissionDenied("Insufficient permissions"),
                ).response()

            return func(*args, **kwargs)

        return wrapper

    return decorator


def require_any_permission(permissions: List[str]):
    """Decorator for requiring any of the specified permissions"""

    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            request = args[1] if len(args) > 1 else None

            if not request or not hasattr(request, "staff"):
                raise PermissionDenied("No user context available")

            if not request.is_authenticated:
                return Response(
                    {"error": "Authentication required"},
                    status=status.HTTP_401_UNAUTHORIZED,
                )

            if not AuthorizationService.has_any_permission(request.staff, permissions):
                return Response(
                    {"error": "Insufficient permissions"},
                    status=status.HTTP_403_FORBIDDEN,
                )

            return func(*args, **kwargs)

        return wrapper

    return decorator


def require_role(role: str):
    """Decorator for requiring specific role"""

    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            request = args[1] if len(args) > 1 else None

            if not request or not hasattr(request, "staff"):
                raise PermissionDenied("No user context available")

            if not request.is_authenticated:
                return Response(
                    {"error": "Authentication required"},
                    status=status.HTTP_401_UNAUTHORIZED,
                )

            if request.staff.role != role:
                return Response(
                    {"error": "Insufficient role permissions"},
                    status=status.HTTP_403_FORBIDDEN,
                )

            return func(*args, **kwargs)

        return wrapper

    return decorator
