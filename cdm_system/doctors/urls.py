from django.urls import path

from . import views

urlpatterns = [
    # 工作台
    path("", views.dashboard, name="doctor_dashboard"),
    path("api/stats/", views.dashboard_stats_api, name="api_doctor_stats"),

    # 患者管理
    path("patients/", views.patient_list, name="doctor_patients"),
    path("patients/create/", views.patient_create, name="doctor_patient_create"),
    path("patients/<int:patient_id>/", views.patient_detail, name="doctor_patient_detail"),
    path("patients/<int:patient_id>/edit/", views.patient_edit, name="doctor_patient_edit"),
    path("patients/<int:patient_id>/api/health-trend/", views.patient_health_trend_api, name="api_patient_health_trend"),
    path("patients/<int:patient_id>/api/risk-history/", views.patient_risk_history_api, name="api_patient_risk_history"),
    path("patients/<int:patient_id>/api/adherence/", views.patient_adherence_api, name="api_patient_adherence"),

    # 风险预警
    path("alerts/", views.risk_alerts, name="doctor_alerts"),

    # 随访管理
    path("visits/", views.visit_list, name="doctor_visits"),
    path("visits/<int:visit_id>/complete/", views.visit_complete, name="doctor_visit_complete"),
    path("visits/<int:visit_id>/defer/", views.visit_defer, name="doctor_visit_defer"),

    # 用药监控
    path("medication/", views.medication_monitor, name="doctor_medication"),
    path("medication/plan/<int:patient_id>/create/", views.medication_plan_create, name="doctor_med_plan_create"),
    path("medication/plan/<int:plan_id>/edit/", views.medication_plan_edit, name="doctor_med_plan_edit"),
]
