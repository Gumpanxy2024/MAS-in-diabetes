import logging
from datetime import timedelta

from django.utils import timezone

from doctors.models import VisitTask
from patients.models import Patient
from .state import SystemState

logger = logging.getLogger(__name__)

VISIT_RULES = {
    "green":  {"visit_type": "online",  "days": 30, "priority": "normal"},
    "yellow": {"visit_type": "online",  "days": 14, "priority": "normal"},
    "red":    {"visit_type": "offline", "days": 0,  "priority": "urgent"},
}


def run(state: SystemState) -> SystemState:
    """SchedulerAgent LangGraph节点入口。"""
    patient_id = state["patient_id"]
    risk_level = state.get("risk_level", "green")

    rule = VISIT_RULES.get(risk_level, VISIT_RULES["green"])

    patient = Patient.objects.select_related("doctor").get(pk=patient_id)
    doctor = patient.doctor

    if not doctor:
        logger.warning("患者 %s 未指定责任医生，跳过随访调度", patient.name)
        state["flow_log"] = state.get("flow_log", []) + [
            {"agent": "SchedulerAgent", "time": timezone.now().isoformat(), "action": "跳过：无责任医生"}
        ]
        return state

    if rule["days"] == 0:
        due_date = timezone.now().date()
    else:
        due_date = timezone.now().date() + timedelta(days=rule["days"])

    pending_task = VisitTask.objects.filter(
        patient_id=patient_id,
        status="pending",
    ).order_by("-created_at").first()

    if pending_task:
        pending_task.due_date = due_date
        pending_task.visit_type = rule["visit_type"]
        pending_task.priority = rule["priority"]
        pending_task.save(update_fields=["due_date", "visit_type", "priority"])
        task = pending_task
    else:
        task = VisitTask.objects.create(
            patient=patient,
            doctor=doctor,
            visit_type=rule["visit_type"],
            priority=rule["priority"],
            due_date=due_date,
        )

    state["visit_task_id"] = task.pk
    state["next_visit_date"] = due_date.isoformat()
    state["flow_log"] = state.get("flow_log", []) + [
        {
            "agent": "SchedulerAgent",
            "time": timezone.now().isoformat(),
            "action": f"随访任务{'更新' if pending_task else '创建'}: {rule['visit_type']}, 截止{due_date}",
        }
    ]
    return state
