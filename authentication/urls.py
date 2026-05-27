from django.urls import path

from .views import GoogleLoginView, LogoutView, MeView, TokenRefreshView

app_name = "authentication"

urlpatterns = [
    # POST - Recebe id_token do Google e retorna JWT + dados do user
    path("google/", GoogleLoginView.as_view(), name="google-login"),
    # POST - Renova o access token com o refresh token
    path("token/refresh/", TokenRefreshView.as_view(), name="token-refresh"),
    # POST - Invalida o refresh token (logout)
    path("logout/", LogoutView.as_view(), name="logout"),
    # GET - Retorna dados do utilizador autenticado
    path("me/", MeView.as_view(), name="me"),
]
