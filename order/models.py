import uuid
from django.db import models
from accounts.models import User
from products.models import Product


class Order(models.Model):
    class Status(models.TextChoices):
        CREATED = "CREATED", "Created"
        REQUIRES_PAYMENT = "REQUIRES_PAYMENT", "Requires payment"
        COMPLETED = "COMPLETED", "Completed"

    class PaymentStatus(models.TextChoices):
        UNPAID = "UNPAID", "Unpaid"
        PAID = "PAID", "Paid"
        FAILED = "FAILED", "Failed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order_number = models.CharField(max_length=32, unique=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="orders")
    amount_toman = models.BigIntegerField()

    status = models.CharField(max_length=32, choices=Status.choices, default=Status.CREATED)
    payment_status = models.CharField(max_length=16, choices=PaymentStatus.choices, default=PaymentStatus.UNPAID)

    created_at = models.DateTimeField(auto_now_add=True)


class Checkout(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name="checkout")

    phone = models.CharField(max_length=32)
    national_id = models.CharField(max_length=10)

    city = models.CharField(max_length=64)
    address = models.TextField()
    postal_code = models.CharField(max_length=10)

    client_total_toman = models.BigIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)


class CheckoutItem(models.Model):
    checkout = models.ForeignKey(Checkout, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="checkout_items")
    quantity = models.PositiveIntegerField()
    unit_price_toman = models.BigIntegerField()
    line_total_toman = models.BigIntegerField()