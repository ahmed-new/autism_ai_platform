# specialist_portal/urls.py
from django.urls import path
from .views import specialist_home, approve_link, reject_link

urlpatterns = [
    path("", specialist_home, name="specialist_home"),
    path("requests/<int:pk>/approve/", approve_link, name="approve_link"),
    path("requests/<int:pk>/reject/", reject_link, name="reject_link"),
]
