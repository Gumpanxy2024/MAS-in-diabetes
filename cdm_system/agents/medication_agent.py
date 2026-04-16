import logging
from datetime import timedelta

from django.utils import timezone
from django.db.models import Count, Q

from doctors.models import MedicationPlan
from patients.models import MedicationRecord
from .state import SystemState

logger = logging.getLogger(__name__)

REFILL_THRESHOLD = 3


def handle_checkin(plan_id: int, patient_id: int, status: str = "taken") -> MedicationRecord:
    """记录一次用药打卡。"""
    record = MedicationRecord.objects.create(
        plan_id=plan_id,
        patient_id=patient_id,
        scheduled_time=timezone.now(),
        checked_at=timezone.now() if status == "taken" else None,
        status=status,
    )
    return record


def calculate_adherence_rate(patient_id: int, days: int = 30) -> float:
    """计算指定时间窗口内的用药依从率。"""
    cutoff = timezone.now() - timedelta(days=days)
    records = MedicationRecord.objects.filter(
        patient_id=patient_id,
        scheduled_time__gte=cutoff,
    )
    total = records.count()
    if total == 0:
        return 100.0
    taken = records.filter(status="taken").count()
    return round((taken / total) * 100, 1)


def estimate_remaining_days(plan_id: int) -> int:
    """估算某用药方案的剩余天数。"""
    try:
        plan = MedicationPlan.objects.get(pk=plan_id)
        return plan.remaining_days
    except MedicationPlan.DoesNotExist:
        return 0


def check_refill_needed(plan_id: int) -> bool:
    """检查是否需要续方。"""
    remaining = estimate_remaining_days(plan_id)
    return remaining <= REFILL_THRESHOLD


def run_reminder_check() -> list[dict]:
    """
    定时任务入口：检查所有活跃方案的续方需求。
    返回需要续方提醒的方案列表。
    """
    alerts = []
    active_plans = MedicationPlan.objects.filter(is_active=True)
    for plan in active_plans:
        if plan.refill_needed:
            alerts.append({
                "plan_id": plan.pk,
                "patient_id": plan.patient_id,
                "patient_name": plan.patient.name,
                "drug_name": plan.drug_name,
                "remaining_days": plan.remaining_days,
            })
    return alerts
