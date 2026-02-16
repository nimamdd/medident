from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from order.models import Order, DailySales
from order.serializers import (
    CheckoutCreateSerializer,
    OrderReadSerializer,
    PaymentUpdateSerializer,
    OrderListDetailedSerializer,
    AdminFulfillmentUpdateSerializer,
    DailySalesReadSerializer,
    AdminDashboardOverviewSerializer,
)
from order.services import create_order_from_checkout, record_daily_sales_for_order
from products.permissions import IsAdmin


class CheckoutCreateView(APIView):
    """
    Create an order and checkout from cart items.

    Auth:
      - Requires: Authorization: Bearer <access_token>

    POST input (JSON):
      - phone: string
      - nationalId: string (10 chars)
      - city: string
      - address: string
      - postalCode: string (10 chars)
      - clientTotalToman: int
      - items: list[{productId: uuid, quantity: int>=1}]

    Responses:
      - 201 Created: order details
      - 400 Bad Request: validation or stock/pricing error
      - 401 Unauthorized: missing/invalid token
    """

    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request):
        s = CheckoutCreateSerializer(data=request.data)
        s.is_valid(raise_exception=True)

        try:
            order = create_order_from_checkout(
                request.user,
                phone=s.validated_data["phone"],
                national_id=s.validated_data["nationalId"],
                city=s.validated_data["city"],
                address=s.validated_data["address"],
                postal_code=s.validated_data["postalCode"],
                client_total_toman=s.validated_data["clientTotalToman"],
                items=s.validated_data["items"],
            )
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(OrderReadSerializer(order).data, status=status.HTTP_201_CREATED)


class OrderListView(generics.ListAPIView):
    """
    List current user's orders (newest first).

    Auth:
      - Requires: Authorization: Bearer <access_token>

    Responses:
      - 200 OK: list of orders with checkout items
      - 401 Unauthorized: missing/invalid token
    """

    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = OrderListDetailedSerializer

    def get_queryset(self):
        return (
            Order.objects.filter(user=self.request.user)
            .select_related("checkout")
            .prefetch_related("checkout__items", "checkout__items__product")
            .order_by("-created_at")
        )


class OrderDetailView(generics.RetrieveAPIView):
    """
    Retrieve an order by order number for current user.

    Auth:
      - Requires: Authorization: Bearer <access_token>

    URL params:
      - order_number: string

    Responses:
      - 200 OK: order details
      - 401 Unauthorized: missing/invalid token
      - 404 Not Found: order not found
    """

    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = OrderReadSerializer
    lookup_field = "order_number"

    def get_queryset(self):
        return Order.objects.filter(user=self.request.user).select_related("checkout").prefetch_related(
            "checkout__items",
            "checkout__items__product",
        )


class OrderPaymentUpdateView(APIView):
    """
    Update payment status for an order (placeholder for payment gateway callback).

    Auth:
      - Requires: Authorization: Bearer <access_token>

    PATCH input (JSON):
      - paymentStatus: UNPAID|PAID|FAILED

    Responses:
      - 200 OK: updated order
      - 400 Bad Request: validation error
      - 401 Unauthorized: missing/invalid token
      - 404 Not Found: order not found
    """

    permission_classes = (permissions.IsAuthenticated,)

    def patch(self, request, order_number):
        order = generics.get_object_or_404(Order, order_number=order_number, user=request.user)

        s = PaymentUpdateSerializer(data=request.data)
        s.is_valid(raise_exception=True)

        was_paid = order.payment_status == Order.PaymentStatus.PAID
        order.payment_status = s.validated_data["paymentStatus"]
        if order.payment_status == Order.PaymentStatus.PAID:
            order.status = Order.Status.COMPLETED
        order.save(update_fields=["payment_status", "status"])

        if not was_paid and order.payment_status == Order.PaymentStatus.PAID:
            record_daily_sales_for_order(order)

        return Response(OrderReadSerializer(order).data, status=status.HTTP_200_OK)


class AdminOrderListView(generics.ListAPIView):
    """
    Admin list all orders with checkout details (newest first).

    Auth:
      - Requires: Authorization: Bearer <access_token>
      - Requires: is_admin == True

    Responses:
      - 200 OK: list of orders
      - 401 Unauthorized: missing/invalid token
      - 403 Forbidden: not admin
    """

    permission_classes = (IsAdmin,)
    serializer_class = OrderListDetailedSerializer

    def get_queryset(self):
        return (
            Order.objects.all()
            .select_related("user", "checkout")
            .prefetch_related("checkout__items", "checkout__items__product")
            .order_by("-created_at")
        )


class AdminOrderDetailView(generics.RetrieveAPIView):
    """
    Admin retrieve order details by order number.

    Auth:
      - Requires: Authorization: Bearer <access_token>
      - Requires: is_admin == True

    URL params:
      - order_number: string

    Responses:
      - 200 OK: order details
      - 401 Unauthorized: missing/invalid token
      - 403 Forbidden: not admin
      - 404 Not Found: order not found
    """

    permission_classes = (IsAdmin,)
    serializer_class = OrderReadSerializer
    lookup_field = "order_number"

    def get_queryset(self):
        return Order.objects.select_related("user", "checkout").prefetch_related(
            "checkout__items",
            "checkout__items__product",
        )


class AdminOrderFulfillmentUpdateView(APIView):
    """
    Admin update fulfillment status for orders.

    Auth:
      - Requires: Authorization: Bearer <access_token>
      - Requires: is_admin == True

    URL params:
      - order_number: string

    PATCH input (JSON):
      - fulfillmentStatus: UNTRACKED|FAILED|SHIPPING|SHIPPED

    Responses:
      - 200 OK: updated order
      - 400 Bad Request: validation error
      - 401 Unauthorized: missing/invalid token
      - 403 Forbidden: not admin
      - 404 Not Found: order not found
    """

    permission_classes = (IsAdmin,)

    def patch(self, request, order_number):
        order = generics.get_object_or_404(Order, order_number=order_number)

        s = AdminFulfillmentUpdateSerializer(data=request.data)
        s.is_valid(raise_exception=True)

        order.fulfillment_status = s.validated_data["fulfillmentStatus"]
        order.save(update_fields=["fulfillment_status"])

        return Response(OrderReadSerializer(order).data, status=status.HTTP_200_OK)


class AdminDailySalesListView(generics.ListAPIView):
    """
    Admin list daily sales aggregates (newest first).

    Auth:
      - Requires: Authorization: Bearer <access_token>
      - Requires: is_admin == True

    Responses:
      - 200 OK: list of daily sales rows
      - 401 Unauthorized: missing/invalid token
      - 403 Forbidden: not admin
    """

    permission_classes = (IsAdmin,)
    serializer_class = DailySalesReadSerializer

    def get_queryset(self):
        return DailySales.objects.all().order_by("-date")


class AdminDashboardOverviewView(APIView):
    """
    Admin dashboard overview metrics.

    Auth:
      - Requires: Authorization: Bearer <access_token>
      - Requires: is_admin == True

    Response:
      - 200 OK: dashboard metrics
        {
          "totalRevenueToman": int,
          "totalOrders": int,
          "totalCustomers": int,
          "conversionRate": float,
          "topProducts": [{"productId": uuid, "productTitle": string, "quantitySold": int}]
        }
      - 401 Unauthorized: missing/invalid token
      - 403 Forbidden: not admin
    """

    permission_classes = (IsAdmin,)

    def get(self, request):
        from django.db.models import Sum, Count
        from django.db.models.functions import Coalesce

        paid_orders = Order.objects.filter(payment_status=Order.PaymentStatus.PAID)

        totals = paid_orders.aggregate(
            total_revenue=Coalesce(Sum("amount_toman"), 0),
            total_orders=Coalesce(Count("id"), 0),
        )

        total_customers = Order.objects.values("user_id").distinct().count()
        conversion_rate = (totals["total_orders"] / total_customers) if total_customers else 0

        top_products = (
            paid_orders.values(
                "checkout__items__product_id",
                "checkout__items__product__title",
            )
            .annotate(quantity_sold=Coalesce(Sum("checkout__items__quantity"), 0))
            .order_by("-quantity_sold")[:5]
        )

        payload = {
            "totalRevenueToman": totals["total_revenue"],
            "totalOrders": totals["total_orders"],
            "totalCustomers": total_customers,
            "conversionRate": round(conversion_rate, 4),
            "topProducts": [
                {
                    "productId": row["checkout__items__product_id"],
                    "productTitle": row["checkout__items__product__title"],
                    "quantitySold": row["quantity_sold"],
                }
                for row in top_products
                if row["checkout__items__product_id"]
            ],
        }

        s = AdminDashboardOverviewSerializer(payload)
        return Response(s.data, status=status.HTTP_200_OK)
