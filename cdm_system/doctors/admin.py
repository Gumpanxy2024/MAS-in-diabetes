from django.contrib import admin

from .models import Doctor, VisitTask, MedicationPlan


@admin.register(Doctor)
class DoctorAdmin(admin.ModelAdmin):
    list_display = ("name", "user", "created_at")


@admin.register(VisitTask)
class VisitTaskAdmin(admin.ModelAdmin):
    list_display = ("patient", "doctor", "visit_type", "priority", "due_date", "status")
    list_filter = ("status", "priority", "visit_type")


@admin.register(MedicationPlan)
class MedicationPlanAdmin(admin.ModelAdmin):
    list_display = ("patient", "drug_name", "dosage", "frequency", "start_date", "is_active")
    list_filter = ("is_active",)
