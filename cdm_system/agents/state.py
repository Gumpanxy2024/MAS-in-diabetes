from typing import TypedDict, Optional


class SystemState(TypedDict):
    patient_id: int
    patient_name: str
    raw_input: str
    input_type: str                      # "voice" / "text"
    health_record: dict
    health_record_id: Optional[int]
    risk_level: str                      # "green" / "yellow" / "red"
    risk_score: float
    previous_risk_level: str
    trigger_indicators: list
    visit_task_id: Optional[int]
    next_visit_date: Optional[str]
    medication_alert: bool
    flow_log: list
