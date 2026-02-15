import uuid
from django.db import models
from accounts.models import User
from products.models import Product


class Order(models.Model):
    class Status(models.TextChoices):
        CREATED = "CREATED", "ایجاد شده"
        REQUIRES_PAYMENT = "REQUIRES_PAYMENT", "نیازمند پرداخت"
        COMPLETED = "COMPLETED", "تکمیل شده"

    class PaymentStatus(models.TextChoices):
        UNPAID = "UNPAID", "پرداخت نشده"
        PAID = "PAID", "پرداخت شده"
        FAILED = "FAILED", "ناموفق"

    class FulfillmentStatus(models.TextChoices):
        UNTRACKED = "UNTRACKED", "پیگیری نشده"
        FAILED = "FAILED", "ناموفق"
        SHIPPING = "SHIPPING", "در حال ارسال"
        SHIPPED = "SHIPPED", "ارسال شده"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order_number = models.CharField(max_length=32, unique=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="orders")
    amount_toman = models.BigIntegerField()

    status = models.CharField(max_length=32, choices=Status.choices, default=Status.CREATED)
    payment_status = models.CharField(max_length=16, choices=PaymentStatus.choices, default=PaymentStatus.UNPAID)
    fulfillment_status = models.CharField(
        max_length=16,
        choices=FulfillmentStatus.choices,
        default=FulfillmentStatus.UNTRACKED,
    )

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


class DailySales(models.Model):
    date = models.DateField(unique=True)
    total_toman = models.BigIntegerField(default=0)
    orders_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-date"]

    def __str__(self):
        return f"{self.date}"
