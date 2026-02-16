from django.urls import path

from order.views import (
    CheckoutCreateView,
    OrderListView,
    OrderDetailView,
    OrderPaymentUpdateView,
    AdminOrderListView,
    AdminOrderDetailView,
    AdminOrderFulfillmentUpdateView,
    AdminDailySalesListView,
    AdminDashboardOverviewView,
)


urlpatterns = [
    path("checkout/", CheckoutCreateView.as_view(), name="checkout-create"),
    path("orders/", OrderListView.as_view(), name="order-list"),
    path("orders/<str:order_number>/", OrderDetailView.as_view(), name="order-detail"),
    path("orders/<str:order_number>/payment/", OrderPaymentUpdateView.as_view(), name="order-payment"),

    path("admin/orders/", AdminOrderListView.as_view(), name="admin-order-list"),
    path("admin/orders/<str:order_number>/", AdminOrderDetailView.as_view(), name="admin-order-detail"),
    path("admin/orders/<str:order_number>/fulfillment/", AdminOrderFulfillmentUpdateView.as_view(), name="admin-order-fulfillment"),
    path("admin/sales/daily/", AdminDailySalesListView.as_view(), name="admin-daily-sales"),
    path("admin/dashboard/overview/", AdminDashboardOverviewView.as_view(), name="admin-dashboard-overview"),
]
