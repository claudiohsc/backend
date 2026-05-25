from django.urls import path
from .views import AdminDashboardView

app_name = 'dashboard'

urlpatterns = [
    path('summary/', AdminDashboardView.as_view(), name='dashboard_summary'),
]