import uuid
from django.db import models
from django.contrib.auth.models import AbstractUser
from core.constants import PHONE_LENGTH, NAME_LENGTH, STATUS_LENGTH, DEFAULT_ROLE


class Staff(AbstractUser):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    phone = models.CharField(max_length=PHONE_LENGTH)
    class Role(models.TextChoices):
        ADMIN = 'ADMIN', 'Admin'
        MANAGER = 'MANAGER', 'Manager'
        SALES = 'SALES', 'Sales'
    
    name = models.CharField(max_length=NAME_LENGTH)
    role = models.CharField(max_length=STATUS_LENGTH, choices=Role.choices, default=DEFAULT_ROLE)
    is_active = models.BooleanField(default=True)
    last_login = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'staff'
        verbose_name = 'Staff'
        verbose_name_plural = 'Staff'

    def __str__(self):
        return f"{self.name} ({self.role})"



class Customer(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=NAME_LENGTH)
    phone = models.CharField(max_length=PHONE_LENGTH)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'customers'
        verbose_name = 'Customer'
        verbose_name_plural = 'Customers'

    def __str__(self):
        return self.name
