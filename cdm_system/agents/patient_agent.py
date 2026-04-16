import json
import logging

from django.utils import timezone

from patients.models import Patient, HealthRecord
from .state import SystemState

logger = logging.getLogger(__name__)

LLM_PROMPT_TEMPLATE = """你是一个医疗数据解析助手。请从以下患者口述文字中提取体征数据，
以JSON格式输出，字段包括：
- fasting_glucose（空腹血糖，单位mmol/L）
- postmeal_glucose（餐后血糖，单位mmol/L）
- systolic_bp（收缩压，单位mmHg）
- diastolic_bp（舒张压，单位mmHg）
- weight（体重，单位kg）
若某字段未提及，值填null。仅输出JSON，不要添加任何解释文字。

患者描述：{input_text}"""

VALID_RANGES = {
    "fasting_glucose": (1.0, 35.0),
    "postmeal_glucose": (1.0, 40.0),
    "systolic_bp": (60, 260),
    "diastolic_bp": (30, 160),
    "weight": (20.0, 200.0),
}


def parse_voice_text(text: str) -> dict:
    """调用LLM解析口语化文本为结构化JSON。"""
    try:
        from langchain_openai import ChatOpenAI
        from django.conf import settings

        llm = ChatOpenAI(
            model=getattr(settings, "LLM_MODEL", "gpt-4o-mini"),
            api_key=getattr(settings, "LLM_API_KEY", ""),
            base_url=getattr(settings, "LLM_BASE_URL", None),
            temperature=0,
        )
        prompt = LLM_PROMPT_TEMPLATE.format(input_text=text)
        response = llm.invoke(prompt)
        content = response.content.strip()
        if content.startswith("```"):
            content = content.split("\n", 1)[1].rsplit("```", 1)[0].strip()
        return json.loads(content)
    except Exception as e:
        logger.error("LLM解析失败: %s", e)
        return {}


def parse_form_data(data: dict) -> dict:
    """将前端表单提交的数据映射为标准字段。"""
    result = {}
    for field in VALID_RANGES:
        val = data.get(field)
        if val is not None and val != "":
            try:
                result[field] = float(val)
            except (ValueError, TypeError):
                result[field] = None
        else:
            result[field] = None
    return result


def validate_health_data(data: dict) -> dict:
    """校验数值范围，返回清洗后数据。超出范围的字段置为None并记录警告。"""
    cleaned = {}
    for field, val in data.items():
        if val is None or field not in VALID_RANGES:
            cleaned[field] = val
            continue
        lo, hi = VALID_RANGES[field]
        if lo <= float(val) <= hi:
            cleaned[field] = float(val)
        else:
            logger.warning("字段 %s 值 %s 超出合理范围 [%s, %s]", field, val, lo, hi)
            cleaned[field] = None
    return cleaned


def save_health_record(patient_id: int, data: dict, input_type: str) -> HealthRecord:
    """将结构化数据写入HealthRecord表。"""
    record = HealthRecord.objects.create(
        patient_id=patient_id,
        fasting_glucose=data.get("fasting_glucose"),
        postmeal_glucose=data.get("postmeal_glucose"),
        systolic_bp=data.get("systolic_bp"),
        diastolic_bp=data.get("diastolic_bp"),
        weight=data.get("weight"),
        input_type=input_type,
    )
    return record


def generate_health_feedback(health_data: dict, risk_level: str, patient_id: int = None, user=None) -> str:
    """基于 RAG 生成面向患者的健康反馈建议。结果同时写入 AgentLog。"""
    import time as _time
    start = _time.time()
    feedback = ""
    try:
        from . import rag_service
        feedback = rag_service.generate_patient_feedback(health_data, risk_level)
    except Exception as e:
        logger.warning("健康反馈生成失败: %s", e)

    duration_ms = int((_time.time() - start) * 1000)
    if patient_id:
        _write_log(
            patient_id=patient_id,
            log_type="health_feedback",
            agent_name="PatientAgent",
            raw_input=json.dumps({"health_data": health_data, "risk_level": risk_level}, ensure_ascii=False),
            raw_output=feedback,
            duration_ms=duration_ms,
            user=user,
        )
    return feedback


def _write_log(patient_id, log_type, agent_name, raw_input="", raw_output="",
               context_snapshot=None, health_record=None, duration_ms=None, user=None):
    """安全写入 AgentLog，失败不影响主流程。"""
    try:
        from .models import AgentLog
        AgentLog.objects.create(
            patient_id=patient_id,
            log_type=log_type,
            agent_name=agent_name,
            raw_input=raw_input,
            raw_output=raw_output,
            context_snapshot=context_snapshot,
            health_record=health_record,
            duration_ms=duration_ms,
            created_by=user,
        )
    except Exception as e:
        logger.warning("AgentLog 写入失败: %s", e)


def run(state: SystemState) -> SystemState:
    """PatientAgent LangGraph节点入口。"""
    patient_id = state["patient_id"]
    raw_input = state.get("raw_input", "")
    input_type = state.get("input_type", "text")

    patient = Patient.objects.get(pk=patient_id)
    state["patient_name"] = patient.name

    if input_type == "voice" and raw_input:
        parsed = parse_voice_text(raw_input)
        _write_log(
            patient_id=patient_id,
            log_type="voice_parse",
            agent_name="PatientAgent",
            raw_input=raw_input,
            raw_output=json.dumps(parsed, ensure_ascii=False),
        )
    else:
        parsed = parse_form_data(state.get("health_record", {}))

    cleaned = validate_health_data(parsed)
    record = save_health_record(patient_id, cleaned, input_type)

    state["health_record"] = cleaned
    state["health_record_id"] = record.pk
    state["flow_log"] = state.get("flow_log", []) + [
        {"agent": "PatientAgent", "time": timezone.now().isoformat(), "action": "数据解析与存储完成"}
    ]
    return state
