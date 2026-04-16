import logging
from decimal import Decimal

from django.utils import timezone

from risk.models import RiskRecord
from .state import SystemState

logger = logging.getLogger(__name__)

RISK_WEIGHTS = {
    "fasting_glucose": {"weight": 0.35, "thresholds": (7.0, 13.9)},
    "postmeal_glucose": {"weight": 0.25, "thresholds": (10.0, 16.7)},
    "systolic_bp":      {"weight": 0.20, "thresholds": (130, 160)},
    "diastolic_bp":     {"weight": 0.10, "thresholds": (80, 100)},
    "bmi":              {"weight": 0.10, "thresholds": (24, 28)},
}

LEVEL_THRESHOLDS = (1.5, 2.2)


def _score_indicator(value, thresholds) -> int:
    if value is None:
        return 0
    low, high = thresholds
    if value < low:
        return 1  # 绿
    elif value <= high:
        return 2  # 黄
    else:
        return 3  # 红


def _calculate_bmi(weight, patient_id) -> float | None:
    """根据体重和患者身高计算BMI。"""
    if weight is None:
        return None
    try:
        from patients.models import Patient
        patient = Patient.objects.get(pk=patient_id)
        if patient.height and patient.height > 0:
            height_m = float(patient.height) / 100.0
            return float(weight) / (height_m ** 2)
    except Exception:
        pass
    return None


def calculate_weighted_score(data: dict, patient_id: int) -> tuple[float, list]:
    """
    加权风险评分。
    返回 (加权总分, 异常指标列表)。
    """
    total_score = 0.0
    total_weight = 0.0
    triggers = []

    bmi = _calculate_bmi(data.get("weight"), patient_id)
    eval_data = {**data, "bmi": bmi}

    for indicator, config in RISK_WEIGHTS.items():
        value = eval_data.get(indicator)
        if value is None:
            continue
        score = _score_indicator(float(value), config["thresholds"])
        weighted = score * config["weight"]
        total_score += weighted
        total_weight += config["weight"]

        if score >= 2:
            triggers.append({
                "indicator": indicator,
                "value": float(value),
                "score": score,
                "threshold_yellow": config["thresholds"][0],
                "threshold_red": config["thresholds"][1],
            })

    if total_weight > 0:
        normalized = total_score / total_weight
    else:
        normalized = 1.0

    return round(normalized, 2), triggers


def map_score_to_level(score: float) -> str:
    if score < LEVEL_THRESHOLDS[0]:
        return "green"
    elif score <= LEVEL_THRESHOLDS[1]:
        return "yellow"
    else:
        return "red"


def run(state: SystemState) -> SystemState:
    """TriageAgent LangGraph节点入口。"""
    import json as _json
    patient_id = state["patient_id"]
    health_data = state.get("health_record", {})
    health_record_id = state.get("health_record_id")

    previous_level = "green"
    last_risk = RiskRecord.objects.filter(patient_id=patient_id).order_by("-evaluated_at").first()
    if last_risk:
        previous_level = last_risk.risk_level

    score, triggers = calculate_weighted_score(health_data, patient_id)
    level = map_score_to_level(score)

    risk_record = None
    if health_record_id:
        risk_record = RiskRecord.objects.create(
            patient_id=patient_id,
            health_record_id=health_record_id,
            risk_level=level,
            risk_score=Decimal(str(score)),
            trigger_indicators=triggers,
        )

    try:
        from .models import AgentLog
        from patients.models import HealthRecord
        hr = HealthRecord.objects.filter(pk=health_record_id).first() if health_record_id else None
        AgentLog.objects.create(
            patient_id=patient_id,
            log_type="risk_eval",
            agent_name="TriageAgent",
            raw_input=_json.dumps(health_data, ensure_ascii=False),
            raw_output=_json.dumps({"level": level, "score": score, "triggers": triggers}, ensure_ascii=False),
            health_record=hr,
        )
    except Exception as e:
        logger.warning("AgentLog 写入失败: %s", e)

    state["risk_level"] = level
    state["risk_score"] = score
    state["previous_risk_level"] = previous_level
    state["trigger_indicators"] = triggers
    state["flow_log"] = state.get("flow_log", []) + [
        {
            "agent": "TriageAgent",
            "time": timezone.now().isoformat(),
            "action": f"风险评估完成: {level}({score})",
        }
    ]
    return state
