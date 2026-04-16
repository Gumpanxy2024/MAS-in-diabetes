"""
LangGraph有向图定义。
主业务流程：PatientAgent → TriageAgent → [条件分支] → SchedulerAgent/DoctorAgent → END
"""
from langgraph.graph import StateGraph, END

from .state import SystemState
from . import patient_agent, triage_agent, scheduler_agent, doctor_agent


def should_reschedule(state: SystemState) -> str:
    """条件边：风险等级是否发生变更。"""
    current = state.get("risk_level", "green")
    previous = state.get("previous_risk_level", "green")
    if current != previous:
        return "reschedule"
    if current == "red":
        return "reschedule"
    return "skip"


def build_main_graph() -> StateGraph:
    """构建主业务流程有向图。"""
    graph = StateGraph(SystemState)

    graph.add_node("patient_agent", patient_agent.run)
    graph.add_node("triage_agent", triage_agent.run)
    graph.add_node("scheduler_agent", scheduler_agent.run)
    graph.add_node("doctor_agent", doctor_agent.run)

    graph.set_entry_point("patient_agent")
    graph.add_edge("patient_agent", "triage_agent")
    graph.add_conditional_edges(
        "triage_agent",
        should_reschedule,
        {
            "reschedule": "scheduler_agent",
            "skip": "doctor_agent",
        },
    )
    graph.add_edge("scheduler_agent", "doctor_agent")
    graph.add_edge("doctor_agent", END)

    return graph


main_graph = build_main_graph()
app = main_graph.compile()
