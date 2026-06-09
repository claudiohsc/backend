from django.urls import path

from .views import (
    AdminDashboardView,
    AdminOrderDetailView,
    AdminOrderListView,
    CheckoutAPIView,
    OrderTrackingView,
    PaymentSuccessRedirectView,
)

app_name = "orders"

urlpatterns = [
    path("dashboard/summary/", AdminDashboardView.as_view(), name="dashboard_summary"),
    path("checkout/", CheckoutAPIView.as_view(), name="checkout"),
    path(
        "pagamento-sucesso/",
        PaymentSuccessRedirectView.as_view(),
        name="payment-success",
    ),
    path("admin/", AdminOrderListView.as_view(), name="admin_orders_list"),
    path(
        "admin/<uuid:order_id>/",
        AdminOrderDetailView.as_view(),
        name="admin_orders_detail",
    ),
    path(
        "<uuid:order_id>/tracking/",
        OrderTrackingView.as_view(),
        name="order-tracking",
    ),
]
