from django.contrib import admin

from .models import Patient, HealthRecord, MedicationRecord


@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display = ("name", "age", "gender", "doctor", "is_active", "created_at")
    list_filter = ("is_active", "gender")
    search_fields = ("name",)


@admin.register(HealthRecord)
class HealthRecordAdmin(admin.ModelAdmin):
    list_display = (
        "patient", "fasting_glucose", "postmeal_glucose",
        "systolic_bp", "diastolic_bp", "weight", "input_type", "recorded_at",
    )
    list_filter = ("input_type",)


@admin.register(MedicationRecord)
class MedicationRecordAdmin(admin.ModelAdmin):
    list_display = ("patient", "plan", "status", "scheduled_time", "checked_at")
    list_filter = ("status",)
