from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from order.models import Order
from order.serializers import (
    CheckoutCreateSerializer,
    OrderReadSerializer,
    OrderListSerializer,
    PaymentUpdateSerializer,
    OrderListDetailedSerializer,
    AdminFulfillmentUpdateSerializer,
)
from order.services import create_order_from_checkout
from products.permissions import IsAdmin


class CheckoutCreateView(APIView):
    """
    Create an order and checkout from cart items.

    Auth:
      - Requires: Authorization: Bearer <access_token>

    POST input (JSON):
      - phone: string
      - nationalId: string
      - city: string
      - address: string
      - postalCode: string
      - clientTotalToman: int
      - items: list[{productId: uuid, quantity: int}]

    Response:
      - 201 Created: order details
      - 400 Bad Request: validation or stock/pricing error
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
    List current user's orders.

    Auth:
      - Requires: Authorization: Bearer <access_token>
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
    """

    permission_classes = (permissions.IsAuthenticated,)

    def patch(self, request, order_number):
        order = generics.get_object_or_404(Order, order_number=order_number, user=request.user)

        s = PaymentUpdateSerializer(data=request.data)
        s.is_valid(raise_exception=True)

        order.payment_status = s.validated_data["paymentStatus"]
        if order.payment_status == Order.PaymentStatus.PAID:
            order.status = Order.Status.COMPLETED
        order.save(update_fields=["payment_status", "status"])

        return Response(OrderReadSerializer(order).data, status=status.HTTP_200_OK)


class AdminOrderListView(generics.ListAPIView):
    """
    Admin list paid orders with checkout details.
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
    Admin update fulfillment status for paid orders.
    """

    permission_classes = (IsAdmin,)

    def patch(self, request, order_number):
        order = generics.get_object_or_404(Order, order_number=order_number)

        s = AdminFulfillmentUpdateSerializer(data=request.data)
        s.is_valid(raise_exception=True)

        order.fulfillment_status = s.validated_data["fulfillmentStatus"]
        order.save(update_fields=["fulfillment_status"])

        return Response(OrderReadSerializer(order).data, status=status.HTTP_200_OK)
