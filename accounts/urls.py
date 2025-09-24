from django.urls import path
from .views import register, login_view, logout_view, CustomPasswordChangeView


urlpatterns = [
    path("register/", register, name="register"),
    path("login/", login_view, name="login"),
    path("logout/", logout_view, name="logout"),
    path("password-change/", CustomPasswordChangeView.as_view(), name="password_change"),
]
