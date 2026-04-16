from django.contrib import admin

from .models import RiskRecord


@admin.register(RiskRecord)
class RiskRecordAdmin(admin.ModelAdmin):
    list_display = ("patient", "risk_level", "risk_score", "evaluated_at")
    list_filter = ("risk_level",)
