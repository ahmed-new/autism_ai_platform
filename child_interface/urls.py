from django.urls import path
from .views import child_home , start_ai_session

urlpatterns = [
    path("", child_home, name="child_home"),
    path("start/", start_ai_session, name="start_ai_session"),
]
