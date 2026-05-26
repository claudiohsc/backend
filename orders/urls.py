from django.urls import path

from .views import AdminDashboardView 

app_name = "orders"

urlpatterns = [
    path("dashboard/summary/", AdminDashboardView.as_view(), name="dashboard_summary"),
]