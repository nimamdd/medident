from django.urls import path

from order.views import CheckoutCreateView, OrderListView, OrderDetailView, OrderPaymentUpdateView


urlpatterns = [
    path("checkout/", CheckoutCreateView.as_view(), name="checkout-create"),
    path("orders/", OrderListView.as_view(), name="order-list"),
    path("orders/<str:order_number>/", OrderDetailView.as_view(), name="order-detail"),
    path("orders/<str:order_number>/payment/", OrderPaymentUpdateView.as_view(), name="order-payment"),
]

