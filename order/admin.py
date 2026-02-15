from django.contrib import admin

from order.models import Order, Checkout, CheckoutItem


class CheckoutItemInline(admin.TabularInline):
    model = CheckoutItem
    extra = 0
    autocomplete_fields = ("product",)
    readonly_fields = ("line_total_toman",)


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        "order_number",
        "user",
        "amount_toman",
        "status",
        "payment_status",
        "fulfillment_status",
        "created_at",
    )
    list_filter = ("status", "payment_status", "fulfillment_status", "created_at")
    search_fields = ("order_number", "user__phone", "user__email")
    ordering = ("-created_at",)
    date_hierarchy = "created_at"
    raw_id_fields = ("user",)
    readonly_fields = ("created_at",)


@admin.register(Checkout)
class CheckoutAdmin(admin.ModelAdmin):
    list_display = (
        "order",
        "phone",
        "national_id",
        "city",
        "postal_code",
        "client_total_toman",
        "created_at",
    )
    list_filter = ("city", "created_at")
    search_fields = ("order__order_number", "phone", "national_id")
    ordering = ("-created_at",)
    date_hierarchy = "created_at"
    raw_id_fields = ("order",)
    inlines = (CheckoutItemInline,)
    readonly_fields = ("created_at",)


@admin.register(CheckoutItem)
class CheckoutItemAdmin(admin.ModelAdmin):
    list_display = (
        "checkout",
        "product",
        "quantity",
        "unit_price_toman",
        "line_total_toman",
    )
    list_filter = ("product",)
    search_fields = ("product__title", "checkout__order__order_number")
    raw_id_fields = ("checkout", "product")
