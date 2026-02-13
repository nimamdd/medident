from django.contrib import admin
from django.utils import timezone

from .models import (
    Category,
    Product,
    ProductImage,
    ProductSpec,
    ProductSeo,
    ProductDimensions,
    ProductReview,
)


class ProductImageInline(admin.TabularInline):
    """
    Manage Product.images (ManyToMany) from inside Product admin.

    Note:
      - ProductImage is now a gallery model (no FK to Product).
      - We edit the M2M link via the implicit through table.
    """
    model = Product.images.through
    extra = 0
    autocomplete_fields = ("productimage",)


class ProductSpecInline(admin.TabularInline):
    model = ProductSpec
    extra = 0
    fields = ("key", "value")
    readonly_fields = ("id",)


class ProductSeoInline(admin.StackedInline):
    model = ProductSeo
    extra = 0
    fields = ("title", "description", "canonical")
    readonly_fields = ("id",)


class ProductDimensionsInline(admin.StackedInline):
    model = ProductDimensions
    extra = 0
    fields = ("length_mm", "width_mm", "height_mm")
    readonly_fields = ("id",)


class ProductReviewInline(admin.TabularInline):
    model = ProductReview
    extra = 0
    fields = ("author", "rating", "title", "status", "approved_at", "created_at")
    readonly_fields = ("id", "created_at")
    ordering = ("-created_at", "id")
    autocomplete_fields = ("author",)


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("title", "slug", "created_at", "updated_at")
    search_fields = ("title", "slug")
    prepopulated_fields = {"slug": ("title",)}
    readonly_fields = ("id", "created_at", "updated_at")
    ordering = ("title",)


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "slug",
        "category",
        "price_toman",
        "compare_at_price_toman",
        "in_stock",
        "stock_quantity",
        "rating",
        "created_at",
        "updated_at",
    )
    list_filter = ("in_stock", "category", "brand")
    search_fields = ("title", "slug", "sku", "brand", "category__title", "category__slug")
    prepopulated_fields = {"slug": ("title",)}
    readonly_fields = ("id", "created_at", "updated_at")
    ordering = ("-created_at",)

    exclude = ("images",)

    inlines = (
        ProductSeoInline,
        ProductDimensionsInline,
        ProductImageInline,
        ProductSpecInline,
        ProductReviewInline,
    )


@admin.action(description="Approve selected reviews")
def approve_reviews(modeladmin, request, queryset):
    now = timezone.now()
    queryset.update(status=ProductReview.StatusChoices.APPROVED, approved_at=now)


@admin.action(description="Reject selected reviews")
def reject_reviews(modeladmin, request, queryset):
    queryset.update(status=ProductReview.StatusChoices.REJECTED)


@admin.action(description="Mark selected reviews as pending")
def mark_pending_reviews(modeladmin, request, queryset):
    queryset.update(status=ProductReview.StatusChoices.PENDING, approved_at=None)


@admin.register(ProductReview)
class ProductReviewAdmin(admin.ModelAdmin):
    list_display = ("product", "author", "rating", "status", "created_at", "approved_at")
    list_filter = ("status", "rating", "created_at")
    search_fields = (
        "product__title",
        "product__slug",
        "author__phone",
        "author__email",
        "author__first_name",
        "author__last_name",
        "title",
        "body",
    )
    readonly_fields = ("id", "created_at")
    ordering = ("-created_at",)
    autocomplete_fields = ("product", "author")
    actions = (approve_reviews, reject_reviews, mark_pending_reviews)


@admin.register(ProductImage)
class ProductImageAdmin(admin.ModelAdmin):
    """
    ProductImage gallery admin.

    This enables autocomplete in ProductImageInline (search by alt/id).
    """
    list_display = ("id", "alt", "src", "width", "height")
    search_fields = ("alt", "id")
    readonly_fields = ("id",)
    ordering = ("-id",)


@admin.register(ProductSpec)
class ProductSpecAdmin(admin.ModelAdmin):
    list_display = ("product", "key", "value")
    search_fields = ("product__title", "product__slug", "key", "value")
    readonly_fields = ("id",)
    ordering = ("product", "key")


@admin.register(ProductSeo)
class ProductSeoAdmin(admin.ModelAdmin):
    list_display = ("product", "title", "canonical")
    search_fields = ("product__title", "product__slug", "title", "canonical")
    readonly_fields = ("id",)
    ordering = ("product",)


@admin.register(ProductDimensions)
class ProductDimensionsAdmin(admin.ModelAdmin):
    list_display = ("product", "length_mm", "width_mm", "height_mm")
    search_fields = ("product__title", "product__slug")
    readonly_fields = ("id",)
    ordering = ("product",)
