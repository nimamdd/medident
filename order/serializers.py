from rest_framework import serializers

from order.models import Order, Checkout, CheckoutItem, DailySales


class CheckoutItemInputSerializer(serializers.Serializer):
    productId = serializers.UUIDField()
    quantity = serializers.IntegerField(min_value=1)


class CheckoutCreateSerializer(serializers.Serializer):
    phone = serializers.CharField(max_length=32)
    nationalId = serializers.CharField(max_length=10)
    city = serializers.CharField(max_length=64)
    address = serializers.CharField()
    postalCode = serializers.CharField(max_length=10)
    clientTotalToman = serializers.IntegerField(min_value=0)
    items = CheckoutItemInputSerializer(many=True)

    def validate_items(self, value):
        if not value:
            raise serializers.ValidationError("At least one item is required.")
        return value


class CheckoutItemReadSerializer(serializers.ModelSerializer):
    productId = serializers.UUIDField(source="product.id", read_only=True)
    productTitle = serializers.CharField(source="product.title", read_only=True)
    unitPriceToman = serializers.IntegerField(source="unit_price_toman", read_only=True)
    lineTotalToman = serializers.IntegerField(source="line_total_toman", read_only=True)

    class Meta:
        model = CheckoutItem
        fields = ("productId", "productTitle", "quantity", "unitPriceToman", "lineTotalToman")


class CheckoutReadSerializer(serializers.ModelSerializer):
    nationalId = serializers.CharField(source="national_id", read_only=True)
    postalCode = serializers.CharField(source="postal_code", read_only=True)
    clientTotalToman = serializers.IntegerField(source="client_total_toman", read_only=True)
    items = CheckoutItemReadSerializer(many=True, read_only=True)

    class Meta:
        model = Checkout
        fields = (
            "phone",
            "nationalId",
            "city",
            "address",
            "postalCode",
            "clientTotalToman",
            "items",
        )


class OrderListSerializer(serializers.ModelSerializer):
    orderNumber = serializers.CharField(source="order_number", read_only=True)
    amountToman = serializers.IntegerField(source="amount_toman", read_only=True)
    paymentStatus = serializers.CharField(source="payment_status", read_only=True)
    fulfillmentStatus = serializers.CharField(source="fulfillment_status", read_only=True)
    createdAt = serializers.DateTimeField(source="created_at", read_only=True)

    class Meta:
        model = Order
        fields = (
            "orderNumber",
            "amountToman",
            "status",
            "paymentStatus",
            "fulfillmentStatus",
            "createdAt",
        )


class OrderReadSerializer(serializers.ModelSerializer):
    orderNumber = serializers.CharField(source="order_number", read_only=True)
    amountToman = serializers.IntegerField(source="amount_toman", read_only=True)
    paymentStatus = serializers.CharField(source="payment_status", read_only=True)
    fulfillmentStatus = serializers.CharField(source="fulfillment_status", read_only=True)
    createdAt = serializers.DateTimeField(source="created_at", read_only=True)
    checkout = CheckoutReadSerializer(read_only=True)

    class Meta:
        model = Order
        fields = (
            "orderNumber",
            "amountToman",
            "status",
            "paymentStatus",
            "fulfillmentStatus",
            "createdAt",
            "checkout",
        )


class OrderListDetailedSerializer(OrderReadSerializer):
    """Detailed list serializer including checkout items."""

    class Meta(OrderReadSerializer.Meta):
        fields = OrderReadSerializer.Meta.fields


class PaymentUpdateSerializer(serializers.Serializer):
    paymentStatus = serializers.ChoiceField(choices=Order.PaymentStatus.choices)


class AdminFulfillmentUpdateSerializer(serializers.Serializer):
    fulfillmentStatus = serializers.ChoiceField(choices=Order.FulfillmentStatus.choices)


class DailySalesReadSerializer(serializers.ModelSerializer):
    totalToman = serializers.IntegerField(source="total_toman", read_only=True)
    ordersCount = serializers.IntegerField(source="orders_count", read_only=True)

    class Meta:
        model = DailySales
        fields = ("date", "totalToman", "ordersCount")


class AdminTopProductSerializer(serializers.Serializer):
    productId = serializers.UUIDField()
    productTitle = serializers.CharField()
    quantitySold = serializers.IntegerField()


class AdminDashboardOverviewSerializer(serializers.Serializer):
    totalRevenueToman = serializers.IntegerField()
    totalOrders = serializers.IntegerField()
    totalCustomers = serializers.IntegerField()
    conversionRate = serializers.FloatField()
    topProducts = AdminTopProductSerializer(many=True)

