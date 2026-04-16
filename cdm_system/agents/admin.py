from django.contrib import admin

from .models import AgentLog


@admin.register(AgentLog)
class AgentLogAdmin(admin.ModelAdmin):
    list_display = ("patient", "log_type", "agent_name", "duration_ms", "created_at")
    list_filter = ("log_type", "agent_name", "created_at")
    search_fields = ("patient__name", "raw_input", "raw_output")
    readonly_fields = ("patient", "log_type", "agent_name", "raw_input", "raw_output",
                       "context_snapshot", "health_record", "created_by", "duration_ms", "created_at")
    date_hierarchy = "created_at"
