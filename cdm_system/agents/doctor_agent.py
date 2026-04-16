import logging

from django.utils import timezone

from .state import SystemState

logger = logging.getLogger(__name__)


def generate_patient_summary(
    patient_name: str,
    risk_level: str,
    risk_score: float,
    trigger_indicators: list,
    recent_records_summary: str,
    adherence_rate: float,
    patient_id: int = None,
    user=None,
) -> str:
    """基于 RAG 生成面向医生的患者诊疗辅助摘要。结果同时写入 AgentLog。"""
    import json
    import time as _time
    start = _time.time()
    summary = ""
    try:
        from . import rag_service
        summary = rag_service.generate_doctor_summary(
            patient_name, risk_level, risk_score,
            trigger_indicators, recent_records_summary, adherence_rate,
        )
    except Exception as e:
        logger.warning("患者摘要生成失败: %s", e)

    duration_ms = int((_time.time() - start) * 1000)
    if patient_id:
        try:
            from .models import AgentLog
            AgentLog.objects.create(
                patient_id=patient_id,
                log_type="doctor_summary",
                agent_name="DoctorAgent",
                raw_input=json.dumps({
                    "patient_name": patient_name,
                    "risk_level": risk_level,
                    "risk_score": risk_score,
                    "adherence_rate": adherence_rate,
                }, ensure_ascii=False),
                raw_output=summary,
                duration_ms=duration_ms,
                created_by=user,
            )
        except Exception as e:
            logger.warning("AgentLog 写入失败: %s", e)

    return summary


def run(state: SystemState) -> SystemState:
    """
    DoctorAgent LangGraph节点入口。
    汇聚各Agent推送信息，准备看板展示数据。
    实际的看板渲染由Django View完成，此处负责：
    1. 记录流程日志
    2. 整合最终状态摘要
    """
    patient_name = state.get("patient_name", "未知")
    risk_level = state.get("risk_level", "green")
    triggers = state.get("trigger_indicators", [])
    medication_alert = state.get("medication_alert", False)

    actions = []
    if risk_level == "red":
        actions.append(f"红码预警：患者{patient_name}需紧急关注")
    if medication_alert:
        actions.append(f"续方提醒：患者{patient_name}药品即将用完")

    action_str = "; ".join(actions) if actions else "常规更新"

    state["flow_log"] = state.get("flow_log", []) + [
        {
            "agent": "DoctorAgent",
            "time": timezone.now().isoformat(),
            "action": f"工作台更新: {action_str}",
        }
    ]
    return state
