from django.urls import path

from .views import AdminDashboardView, CheckoutAPIView, PaymentSuccessRedirectView

app_name = "orders"

urlpatterns = [
    path("dashboard/summary/", AdminDashboardView.as_view(), name="dashboard_summary"),
    path("checkout/", CheckoutAPIView.as_view(), name="checkout"),
    path(
        "pagamento-sucesso/",
        PaymentSuccessRedirectView.as_view(),
        name="payment-success",
    ),
]
