from django.urls import path
from .views import inventory_summary 

app_name = "products"

urlpatterns = [
    path('inventory/', inventory_summary, name='inventory_summary'),
]