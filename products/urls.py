from django.urls import path

from .views import InventorySummaryView

urlpatterns = [
    path("inventory/", InventorySummaryView.as_view(), name="inventory_summary"),
]
