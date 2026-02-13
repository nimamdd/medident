import uuid
from django.db import models
from accounts.models import User


class Category(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    slug = models.SlugField(unique=True)
    title = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title


class Product(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    slug = models.SlugField(unique=True)
    title = models.CharField(max_length=255)
    short_description = models.TextField()
    description = models.TextField(blank=True, null=True)

    images = models.ManyToManyField(
        "ProductImage",
        related_name="products",
        blank=True,
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    sku = models.CharField(max_length=64, blank=True, null=True)
    brand = models.CharField(max_length=128, blank=True, null=True)

    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name="products")

    price_toman = models.PositiveBigIntegerField()
    compare_at_price_toman = models.PositiveBigIntegerField(blank=True, null=True)

    in_stock = models.BooleanField(default=True)
    stock_quantity = models.PositiveIntegerField(blank=True, null=True)

    rating = models.DecimalField(max_digits=3, decimal_places=2, blank=True, null=True)

    def __str__(self):
        return self.title


class ProductImage(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    alt = models.CharField(max_length=255, blank=True, null=True)
    src = models.ImageField(blank=True, null=True, upload_to='product_images/')
    width = models.PositiveIntegerField(blank=True, null=True)
    height = models.PositiveIntegerField(blank=True, null=True)

    class Meta:
        ordering = ["id"]

class ProductSpec(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="specs")
    key = models.CharField(max_length=128)
    value = models.TextField()

    class Meta:
        unique_together = (("product", "key"),)
        ordering = ["key", "id"]


class ProductSeo(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product = models.OneToOneField(Product, on_delete=models.CASCADE, related_name="seo")
    title = models.CharField(max_length=255, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    canonical = models.URLField(blank=True, null=True)


class ProductDimensions(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product = models.OneToOneField(Product, on_delete=models.CASCADE, related_name="dimensions")
    length_mm = models.PositiveIntegerField(blank=True, null=True)
    width_mm = models.PositiveIntegerField(blank=True, null=True)
    height_mm = models.PositiveIntegerField(blank=True, null=True)


class ProductReview(models.Model):
    class StatusChoices(models.TextChoices):
        PENDING = "pending", "Pending"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="reviews")
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name="reviews")
    rating = models.PositiveSmallIntegerField()
    title = models.CharField(max_length=255, blank=True, null=True)
    body = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    status = models.CharField(max_length=16, choices=StatusChoices, default=StatusChoices.PENDING)
    approved_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ["-created_at", "id"]