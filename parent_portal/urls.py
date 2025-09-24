# parent_portal/urls.py
from django.urls import path
from .views import parent_home, create_child ,assign_specialist
from assessments import views_parent_scq as scq
from . import views_ai_coach

app_name = "parent_portal"  # اختياري لكنه مفيد للـ namespace

urlpatterns = [
    path("", parent_home, name="parent_home"),
    path("create-child/", create_child, name="create_child"),

    # SCQ (بدون تكرار كلمة parent)
    path("<int:child_id>/scq/", scq.scq_form, name="parent_scq_form"),
    path("<int:child_id>/scq/<int:submission_id>/", scq.scq_result, name="parent_scq_result"),


      # Assign specialist
    path("child/<int:child_id>/assign-specialist/", assign_specialist, name="assign_specialist"),

     path("<int:child_id>/coach/", views_ai_coach.parent_ai_coach, name="parent_ai_coach"),  # ← جديد
]
