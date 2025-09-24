# reports/urls.py
from django.urls import path
from assessments.views_reports import (
    child_skills_overview_view,
    skill_detail_view,
    child_skills_overview_api,
    skill_detail_api,
)
from assessments import views_reports as reports



urlpatterns = [
    path("child/<int:child_id>/skills/", child_skills_overview_view, name="child_skills_overview"),
    path("child/<int:child_id>/skills/<int:skill_id>/", skill_detail_view, name="skill_detail"),
    path("child/<int:child_id>/skills/api/", child_skills_overview_api, name="child_skills_overview_api"),
    path("child/<int:child_id>/skills/<int:skill_id>/api/", skill_detail_api, name="skill_detail_api"),
       path("child/<int:child_id>/groups/<int:group_id>/",
         reports.group_skills_view, name="group_skills"),

    
]
