import uuid
from django.db import transaction
from django.db.models import F
from django.utils import timezone

from order.models import Order, Checkout, CheckoutItem
from products.models import Product


def _generate_order_number() -> str:
    # 32-char, URL-safe-ish order number
    return uuid.uuid4().hex[:16].upper()


@transaction.atomic
def create_order_from_checkout(user, *, phone, national_id, city, address, postal_code, client_total_toman, items):
    product_ids = [item["productId"] for item in items]
    products = list(Product.objects.select_for_update().filter(id__in=product_ids))

    by_id = {str(p.id): p for p in products}
    missing = [str(pid) for pid in product_ids if str(pid) not in by_id]
    if missing:
        raise ValueError(f"Products not found: {', '.join(missing)}")

    # Validate stock and compute totals
    line_items = []
    server_total = 0
    for item in items:
        product = by_id[str(item["productId"])]
        quantity = int(item["quantity"])

        if not product.in_stock:
            raise ValueError(f"Product not in stock: {product.title}")
        if product.stock_quantity is not None and quantity > product.stock_quantity:
            raise ValueError(f"Insufficient stock for {product.title}")

        unit_price = int(product.price_toman)
        line_total = unit_price * quantity
        server_total += line_total

        line_items.append(
            {
                "product": product,
                "quantity": quantity,
                "unit_price_toman": unit_price,
                "line_total_toman": line_total,
            }
        )

    # Basic price sanity check against client total (can add tolerance later)
    if int(client_total_toman) != int(server_total):
        raise ValueError("Client total does not match server total.")

    order = Order.objects.create(
        order_number=_generate_order_number(),
        user=user,
        amount_toman=server_total,
        status=Order.Status.REQUIRES_PAYMENT,
        payment_status=Order.PaymentStatus.UNPAID,
        created_at=timezone.now(),
    )

    checkout = Checkout.objects.create(
        order=order,
        phone=phone,
        national_id=national_id,
        city=city,
        address=address,
        postal_code=postal_code,
        client_total_toman=client_total_toman,
    )

    CheckoutItem.objects.bulk_create(
        [
            CheckoutItem(
                checkout=checkout,
                product=item["product"],
                quantity=item["quantity"],
                unit_price_toman=item["unit_price_toman"],
                line_total_toman=item["line_total_toman"],
            )
            for item in line_items
        ]
    )

    # Optional stock decrement; can be toggled later
    for item in line_items:
        product = item["product"]
        if product.stock_quantity is not None:
            Product.objects.filter(id=product.id).update(
                stock_quantity=F("stock_quantity") - item["quantity"]
            )

    return order

