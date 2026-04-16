from django.urls import path

from . import views

urlpatterns = [
    path("", views.dashboard, name="patient_dashboard"),
    path("input/", views.health_input, name="patient_input"),
    path("input/result/", views.health_input_result, name="patient_input_result"),
    path("records/", views.health_records, name="patient_records"),
    path("medication/", views.medication_page, name="patient_medication"),
    path("visits/", views.my_visits, name="patient_visits"),
    path("ai-history/", views.ai_history, name="patient_ai_history"),

    # AJAX / JSON API
    path("api/voice-parse/", views.voice_parse_api, name="api_voice_parse"),
    path("api/voice-upload/", views.voice_upload_api, name="api_voice_upload"),
    path("api/tts/", views.tts_api, name="api_tts"),
    path("api/health-trend/", views.health_trend_api, name="api_health_trend"),
    path("api/medication/checkin/", views.medication_checkin_api, name="api_medication_checkin"),
]
