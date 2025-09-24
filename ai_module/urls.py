from django.urls import path
from .views import generate_question ,verify_answer , gaze_ingest ,end_session ,get_progress
# , end_session, ,gaze_ingest
urlpatterns = [
    path("generate-question/", generate_question, name="generate_question"),
    path("verify-answer/", verify_answer, name="verify_answer"),
    path("end-session/", end_session, name="end_session"),          # جديد
    path("progress/", get_progress, name="get_progress"),  
     path("gaze-ingest/", gaze_ingest, name="gaze_ingest"), 
]
