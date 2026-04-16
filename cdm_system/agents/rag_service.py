"""
RAG 知识服务模块。
统一封装向量检索与 LLM 生成，供 PatientAgent / DoctorAgent 按需调用。
知识库基于 ChromaDB 持久化存储，按 metadata.audience 区分 patient / doctor / both。
"""
import logging
import os
from pathlib import Path
from typing import Optional

from django.conf import settings

logger = logging.getLogger(__name__)

_KNOWLEDGE_DIR = Path(settings.BASE_DIR) / "knowledge_base"
_CHROMA_DIR = Path(settings.BASE_DIR) / "chroma_db"

COLLECTION_NAME = "diabetes_kb"


def _get_chroma_client():
    import chromadb
    return chromadb.PersistentClient(path=str(_CHROMA_DIR))


def _get_or_create_collection():
    client = _get_chroma_client()
    return client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )


# ─────────────────── 知识库初始化 ───────────────────


def reset_knowledge_base():
    """清空向量库，重建空集合。更新知识库文件后调用此函数再重新导入。"""
    client = _get_chroma_client()
    try:
        client.delete_collection(COLLECTION_NAME)
        logger.info("已删除向量库集合 %s", COLLECTION_NAME)
    except Exception as e:
        logger.warning("删除集合时出错（可能原本不存在）: %s", e)
    client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )


def init_knowledge_base():
    """
    扫描 knowledge_base/ 目录下的 .txt 文件，按段落切分后写入 ChromaDB。
    文件名约定：
      - patient_*.txt  → audience = "patient"
      - doctor_*.txt   → audience = "doctor"
      - 其他           → audience = "both"
    每个段落以空行分隔，过短段落（<20字）自动跳过。
    """
    collection = _get_or_create_collection()
    if collection.count() > 0:
        logger.info("知识库已有 %d 条记录，跳过初始化", collection.count())
        return collection.count()

    if not _KNOWLEDGE_DIR.exists():
        logger.warning("知识库目录 %s 不存在，跳过初始化", _KNOWLEDGE_DIR)
        return 0

    doc_id = 0
    for txt_file in sorted(_KNOWLEDGE_DIR.glob("*.txt")):
        name = txt_file.stem.lower()
        if name.startswith("patient"):
            audience = "patient"
        elif name.startswith("doctor"):
            audience = "doctor"
        else:
            audience = "both"

        content = txt_file.read_text(encoding="utf-8")
        paragraphs = [p.strip() for p in content.split("\n\n") if len(p.strip()) >= 20]

        if not paragraphs:
            continue

        ids = [f"{name}_{i}" for i in range(len(paragraphs))]
        metadatas = [{"source": txt_file.name, "audience": audience}] * len(paragraphs)

        collection.add(
            ids=ids,
            documents=paragraphs,
            metadatas=metadatas,
        )
        doc_id += len(paragraphs)
        logger.info("已导入 %s：%d 段落（audience=%s）", txt_file.name, len(paragraphs), audience)

    logger.info("知识库初始化完成，共导入 %d 段落", doc_id)
    return doc_id


# ─────────────────── 检索接口 ───────────────────


def retrieve(query: str, audience: str = "both", top_k: int = 3) -> list[dict]:
    """
    从知识库检索与 query 最相关的 top_k 段落。
    audience: "patient" | "doctor" | "both"
      - patient → 返回 audience in (patient, both) 的结果
      - doctor  → 返回 audience in (doctor, both) 的结果
      - both    → 不过滤
    """
    collection = _get_or_create_collection()
    if collection.count() == 0:
        return []

    where_filter = None
    if audience == "patient":
        where_filter = {"audience": {"$in": ["patient", "both"]}}
    elif audience == "doctor":
        where_filter = {"audience": {"$in": ["doctor", "both"]}}

    results = collection.query(
        query_texts=[query],
        n_results=top_k,
        where=where_filter,
    )

    docs = []
    for i, doc_text in enumerate(results["documents"][0]):
        docs.append({
            "text": doc_text,
            "source": results["metadatas"][0][i].get("source", ""),
            "distance": results["distances"][0][i] if results.get("distances") else None,
        })
    return docs


# ─────────────────── 生成接口 ───────────────────


def generate_with_context(
    query: str,
    context_docs: list[dict],
    system_prompt: str,
    max_tokens: int = 500,
) -> str:
    """
    将检索到的知识片段拼入 Prompt，调用 LLM 生成回答。
    """
    context_text = "\n\n".join(
        f"【知识片段{i+1}】{doc['text']}" for i, doc in enumerate(context_docs)
    )

    user_prompt = f"""请基于以下参考知识回答问题。如果参考知识中没有直接答案，请结合医学常识合理回答，但需注明"仅供参考"。

{context_text}

问题：{query}"""

    try:
        from langchain_openai import ChatOpenAI
        llm = ChatOpenAI(
            model=getattr(settings, "LLM_MODEL", "gpt-4o-mini"),
            api_key=getattr(settings, "LLM_API_KEY", ""),
            base_url=getattr(settings, "LLM_BASE_URL", None),
            temperature=0.3,
            max_tokens=max_tokens,
        )
        from langchain_core.messages import SystemMessage, HumanMessage
        messages = [SystemMessage(content=system_prompt), HumanMessage(content=user_prompt)]
        response = llm.invoke(messages)
        return response.content.strip()
    except Exception as e:
        logger.error("RAG 生成失败: %s", e)
        return ""


# ─────────────────── 面向业务的高级接口 ───────────────────


PATIENT_SYSTEM_PROMPT = (
    "你是一位耐心、温和的社区健康顾问，面向的用户是老年糖尿病患者。"
    "请用通俗易懂、口语化的语言回答，避免过多专业术语。"
    "所有建议末尾请附上'本建议仅供参考，具体诊疗请咨询您的责任医生'。"
)

DOCTOR_SYSTEM_PROMPT = (
    "你是一位经验丰富的内分泌科临床顾问，面向的用户是社区全科医生。"
    "请用专业、简洁、结构化的语言生成患者诊疗辅助摘要。"
    "引用指南时请标注出处。"
)


def generate_patient_feedback(health_data: dict, risk_level: str) -> str:
    """
    患者端：数据提交后生成健康反馈建议。
    """
    indicators = []
    if health_data.get("fasting_glucose"):
        indicators.append(f"空腹血糖 {health_data['fasting_glucose']} mmol/L")
    if health_data.get("postmeal_glucose"):
        indicators.append(f"餐后血糖 {health_data['postmeal_glucose']} mmol/L")
    if health_data.get("systolic_bp"):
        indicators.append(f"血压 {health_data.get('systolic_bp')}/{health_data.get('diastolic_bp', '?')} mmHg")

    query = f"患者今日体征：{'，'.join(indicators)}。风险等级：{risk_level}。请给出健康管理建议。"

    docs = retrieve(query, audience="patient", top_k=3)
    if not docs:
        return ""

    return generate_with_context(query, docs, PATIENT_SYSTEM_PROMPT, max_tokens=300)


def generate_doctor_summary(
    patient_name: str,
    risk_level: str,
    risk_score: float,
    trigger_indicators: list,
    recent_records_summary: str,
    adherence_rate: float,
) -> str:
    """
    医生端：打开患者详情时生成智能诊疗摘要。
    """
    query = (
        f"患者{patient_name}，当前风险等级{risk_level}（评分{risk_score}），"
        f"异常指标：{', '.join(trigger_indicators) if trigger_indicators else '无'}。"
        f"近期数据概要：{recent_records_summary}。"
        f"30天用药依从率：{adherence_rate}%。"
        f"请生成诊疗辅助摘要，包含风险分析、管理建议和随访要点。"
    )

    docs = retrieve(query, audience="doctor", top_k=3)
    if not docs:
        return ""

    return generate_with_context(query, docs, DOCTOR_SYSTEM_PROMPT, max_tokens=500)
