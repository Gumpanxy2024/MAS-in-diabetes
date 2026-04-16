"""
CDM System 基础功能测试脚本
测试范围：Django 环境 / 数据库 ORM / LLM API / TTS API / RAG 知识库 / 风险评估
运行方式：cd cdm_system && python ../test/basefunction/run_tests.py
"""
import json
import os
import sys
import time
import traceback
from datetime import datetime
from pathlib import Path

CDM_DIR = Path(__file__).resolve().parent.parent.parent / "cdm_system"
sys.path.insert(0, str(CDM_DIR))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "cdm_system.settings")

RESULTS = []
OUTPUT_DIR = Path(__file__).resolve().parent


def record(test_id: str, name: str, status: str, detail: str = "", duration_ms: int = 0):
    entry = {
        "id": test_id,
        "name": name,
        "status": status,
        "detail": detail,
        "duration_ms": duration_ms,
    }
    RESULTS.append(entry)
    icon = "PASS" if status == "pass" else "FAIL" if status == "fail" else "SKIP"
    print(f"  [{icon}] {test_id} {name} ({duration_ms}ms) {detail[:80] if detail else ''}")


# ═══════════════════ T-01  Django 启动 & .env 加载 ═══════════════════

def test_django_setup():
    t0 = time.time()
    try:
        import django
        django.setup()

        from django.conf import settings
        assert settings.DASHSCOPE_API_KEY, "DASHSCOPE_API_KEY 为空，请检查 .env 文件"
        assert settings.LLM_MODEL == "qwen3.5-plus" or settings.LLM_MODEL, "LLM_MODEL 未配置"

        detail = f"LLM_MODEL={settings.LLM_MODEL}, ASR={settings.ASR_PROVIDER}/{settings.ASR_MODEL}, TTS={settings.TTS_PROVIDER}/{settings.TTS_MODEL}"
        record("T-01", "Django 启动 + .env 加载", "pass", detail, int((time.time() - t0) * 1000))
    except Exception as e:
        record("T-01", "Django 启动 + .env 加载", "fail", str(e), int((time.time() - t0) * 1000))
        raise  # Django 启动失败则无法继续


# ═══════════════════ T-02  数据库迁移 & ORM 操作 ═══════════════════

def test_database():
    t0 = time.time()
    try:
        from django.core.management import call_command
        call_command("migrate", "--run-syncdb", verbosity=0)

        from accounts.models import User
        from patients.models import Patient, HealthRecord
        from risk.models import RiskRecord
        from agents.models import AgentLog

        test_username = "_test_basefunction_"
        User.objects.filter(username=test_username).delete()
        user = User.objects.create_user(username=test_username, password="test1234", role="patient")
        patient = Patient.objects.create(user=user, name="测试患者", age=65, gender="男", height=170, diagnosis_year=2020)

        hr = HealthRecord.objects.create(
            patient=patient,
            fasting_glucose=7.2,
            postmeal_glucose=11.5,
            systolic_bp=138,
            diastolic_bp=85,
            weight=72.0,
            input_type="form",
        )

        assert hr.pk is not None
        assert HealthRecord.objects.filter(patient=patient).count() == 1

        user.delete()

        detail = f"User/Patient/HealthRecord CRUD 正常, migrate 成功"
        record("T-02", "数据库迁移 & ORM", "pass", detail, int((time.time() - t0) * 1000))
    except Exception as e:
        record("T-02", "数据库迁移 & ORM", "fail", traceback.format_exc()[-200:], int((time.time() - t0) * 1000))


# ═══════════════════ T-03  LLM API 调用（Qwen） ═══════════════════

def test_llm_api():
    t0 = time.time()
    try:
        from langchain_openai import ChatOpenAI
        from django.conf import settings

        llm = ChatOpenAI(
            model=settings.LLM_MODEL,
            api_key=settings.DASHSCOPE_API_KEY or settings.LLM_API_KEY,
            base_url=settings.LLM_BASE_URL,
            temperature=0,
            max_tokens=100,
        )
        response = llm.invoke("请用一句话解释什么是空腹血糖。")
        text = response.content.strip()
        assert len(text) > 5, f"LLM 返回内容过短: {text}"

        detail = f"model={settings.LLM_MODEL}, response={text[:60]}..."
        record("T-03", "LLM API (Qwen)", "pass", detail, int((time.time() - t0) * 1000))
    except Exception as e:
        record("T-03", "LLM API (Qwen)", "fail", str(e)[:200], int((time.time() - t0) * 1000))


# ═══════════════════ T-04  LLM 语音文本解析 ═══════════════════

def test_llm_voice_parse():
    t0 = time.time()
    try:
        from agents.patient_agent import parse_voice_text
        sample_text = "今天早上空腹血糖7.8，血压有点高，上面的140下面的90，体重72公斤"
        result = parse_voice_text(sample_text)

        assert isinstance(result, dict), f"返回类型错误: {type(result)}"
        assert result.get("fasting_glucose") is not None, f"未解析出空腹血糖: {result}"

        detail = f"input='{sample_text[:30]}...', parsed={json.dumps(result, ensure_ascii=False)}"
        record("T-04", "LLM 语音文本解析", "pass", detail, int((time.time() - t0) * 1000))
    except Exception as e:
        record("T-04", "LLM 语音文本解析", "fail", str(e)[:200], int((time.time() - t0) * 1000))


# ═══════════════════ T-05  风险评估算法 ═══════════════════

def test_risk_assessment():
    t0 = time.time()
    try:
        from agents.triage_agent import calculate_weighted_score, map_score_to_level

        green_data = {"fasting_glucose": 5.5, "postmeal_glucose": 7.0, "systolic_bp": 120, "diastolic_bp": 75}
        score_g, triggers_g = calculate_weighted_score(green_data, patient_id=0)
        level_g = map_score_to_level(score_g)
        assert level_g == "green", f"低风险数据应为 green，实际: {level_g}(score={score_g})"

        red_data = {"fasting_glucose": 16.0, "postmeal_glucose": 20.0, "systolic_bp": 170, "diastolic_bp": 110}
        score_r, triggers_r = calculate_weighted_score(red_data, patient_id=0)
        level_r = map_score_to_level(score_r)
        assert level_r == "red", f"高风险数据应为 red，实际: {level_r}(score={score_r})"

        detail = f"green={score_g}/{level_g}, red={score_r}/{level_r}, triggers_red={len(triggers_r)}"
        record("T-05", "风险评估算法", "pass", detail, int((time.time() - t0) * 1000))
    except Exception as e:
        record("T-05", "风险评估算法", "fail", str(e)[:200], int((time.time() - t0) * 1000))


# ═══════════════════ T-06  RAG 知识库初始化 & 检索 ═══════════════════

def test_rag_service():
    t0 = time.time()
    try:
        from agents.rag_service import init_knowledge_base, retrieve

        count = init_knowledge_base()
        assert count >= 0, "知识库初始化返回负数"

        docs = retrieve("糖尿病患者如何控制饮食", audience="patient", top_k=3)

        if count > 0:
            assert len(docs) > 0, "知识库非空但检索结果为空"
            detail = f"知识库 {count} 段落, 检索到 {len(docs)} 条, top1={docs[0]['text'][:40]}..."
        else:
            detail = f"知识库为空(count=0), 检索返回 {len(docs)} 条 (正常)"

        record("T-06", "RAG 知识库初始化 & 检索", "pass", detail, int((time.time() - t0) * 1000))
    except Exception as e:
        record("T-06", "RAG 知识库初始化 & 检索", "fail", str(e)[:200], int((time.time() - t0) * 1000))


# ═══════════════════ T-07  TTS 语音合成（DashScope CosyVoice）═══════════════════

def test_tts_dashscope():
    t0 = time.time()
    try:
        from agents.speech_service import synthesize_speech
        from django.conf import settings as _s
        result = synthesize_speech("您好，今天的血糖数据已经记录成功。", voice=_s.TTS_VOICE)

        if result.get("error"):
            record("T-07", "TTS (DashScope CosyVoice)", "fail", result["error"][:200], int((time.time() - t0) * 1000))
            return

        audio_path = result.get("audio_path", "")
        assert audio_path, "TTS 返回空路径"

        full_path = CDM_DIR / audio_path
        assert full_path.exists(), f"音频文件不存在: {full_path}"
        file_size = full_path.stat().st_size
        assert file_size > 100, f"音频文件过小: {file_size} bytes"

        detail = f"provider={result['provider']}, path={audio_path}, size={file_size}B, latency={result['duration_ms']}ms"
        record("T-07", "TTS (DashScope CosyVoice)", "pass", detail, int((time.time() - t0) * 1000))
    except Exception as e:
        record("T-07", "TTS (DashScope CosyVoice)", "fail", str(e)[:200], int((time.time() - t0) * 1000))


# ═══════════════════ T-08  TTS 备选（Edge TTS 免费） ═══════════════════

def test_tts_edge():
    t0 = time.time()
    try:
        from agents.speech_service import _tts_edge
        audio_path = _tts_edge("测试 Edge TTS 语音合成功能。", "zh-CN-XiaoxiaoNeural")

        full_path = CDM_DIR / audio_path
        assert full_path.exists(), f"音频文件不存在: {full_path}"
        file_size = full_path.stat().st_size
        assert file_size > 100, f"音频文件过小: {file_size} bytes"

        detail = f"voice=zh-CN-XiaoxiaoNeural, path={audio_path}, size={file_size}B"
        record("T-08", "TTS 备选 (Edge TTS)", "pass", detail, int((time.time() - t0) * 1000))
    except Exception as e:
        record("T-08", "TTS 备选 (Edge TTS)", "fail", str(e)[:200], int((time.time() - t0) * 1000))


# ═══════════════════ T-09  RAG + LLM 健康反馈生成 ═══════════════════

def test_health_feedback():
    t0 = time.time()
    try:
        from agents.patient_agent import generate_health_feedback
        health_data = {"fasting_glucose": 8.5, "postmeal_glucose": 13.0, "systolic_bp": 145, "diastolic_bp": 90}
        feedback = generate_health_feedback(health_data, risk_level="yellow")

        if not feedback:
            record("T-09", "RAG + LLM 健康反馈", "fail", "返回空字符串（可能知识库为空或 LLM 调用失败）", int((time.time() - t0) * 1000))
            return

        assert len(feedback) > 20, f"反馈过短: {feedback}"

        detail = f"feedback={feedback[:80]}..."
        record("T-09", "RAG + LLM 健康反馈", "pass", detail, int((time.time() - t0) * 1000))
    except Exception as e:
        record("T-09", "RAG + LLM 健康反馈", "fail", str(e)[:200], int((time.time() - t0) * 1000))


# ═══════════════════ T-10  Seed 数据脚本 ═══════════════════

def test_seed_command():
    t0 = time.time()
    try:
        from django.core.management import call_command
        from io import StringIO
        out = StringIO()
        call_command("seed", "--reset", stdout=out, verbosity=1)
        output = out.getvalue()

        from accounts.models import User
        from patients.models import Patient, HealthRecord
        doc_count = User.objects.filter(role="doctor").count()
        pat_count = Patient.objects.count()
        hr_count = HealthRecord.objects.count()

        assert doc_count >= 1, "Seed 后无医生用户"
        assert pat_count >= 5, f"Seed 后患者数 {pat_count} < 5"
        assert hr_count >= 50, f"Seed 后健康记录数 {hr_count} < 50"

        detail = f"doctors={doc_count}, patients={pat_count}, health_records={hr_count}"
        record("T-10", "Seed 数据脚本", "pass", detail, int((time.time() - t0) * 1000))
    except Exception as e:
        record("T-10", "Seed 数据脚本", "fail", str(e)[:200], int((time.time() - t0) * 1000))


# ═══════════════════ 汇总 & 报告 ═══════════════════

def generate_report():
    total = len(RESULTS)
    passed = sum(1 for r in RESULTS if r["status"] == "pass")
    failed = sum(1 for r in RESULTS if r["status"] == "fail")
    skipped = sum(1 for r in RESULTS if r["status"] == "skip")

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    report = f"""# CDM System 基础功能测试报告

> 生成时间：{now}
> 测试环境：Python {sys.version.split()[0]}, {sys.platform}

## 测试概况

| 指标 | 数值 |
|------|------|
| 总用例数 | {total} |
| 通过 | {passed} |
| 失败 | {failed} |
| 跳过 | {skipped} |
| **通过率** | **{passed/total*100:.1f}%** |

## 详细结果

| 编号 | 测试项 | 结果 | 耗时(ms) | 说明 |
|------|--------|------|----------|------|
"""
    for r in RESULTS:
        icon = "PASS" if r["status"] == "pass" else "FAIL" if r["status"] == "fail" else "SKIP"
        detail_escaped = r["detail"].replace("|", "\\|").replace("\n", " ")[:120]
        report += f"| {r['id']} | {r['name']} | {icon} | {r['duration_ms']} | {detail_escaped} |\n"

    report += f"""
## 测试项说明

| 编号 | 说明 |
|------|------|
| T-01 | 验证 Django 框架启动、.env 文件加载、API Key 配置读取 |
| T-02 | 验证数据库迁移、User/Patient/HealthRecord 模型 CRUD |
| T-03 | 验证 DashScope Qwen LLM API 调用（OpenAI 兼容协议） |
| T-04 | 验证 LLM 解析口语化健康数据为结构化 JSON |
| T-05 | 验证加权风险评分算法（绿/黄/红三级分类） |
| T-06 | 验证 ChromaDB 知识库初始化 + 语义检索 |
| T-07 | 验证 DashScope CosyVoice TTS 语音合成 |
| T-08 | 验证 Edge TTS 免费备选方案 |
| T-09 | 验证 RAG（检索增强生成）健康反馈完整链路 |
| T-10 | 验证 Seed 数据填充脚本（管理命令 python manage.py seed） |

## 结论

"""
    if failed == 0:
        report += "所有基础功能测试均通过，系统核心链路（LLM/TTS/RAG/风险评估/数据库）运行正常。\n"
    else:
        report += f"共 {failed} 项测试未通过，请根据上表中的失败说明排查问题。\n"

    # JSON 原始数据
    json_path = OUTPUT_DIR / "results.json"
    json_path.write_text(json.dumps(RESULTS, ensure_ascii=False, indent=2), encoding="utf-8")

    report_path = OUTPUT_DIR / "report.md"
    report_path.write_text(report, encoding="utf-8")

    print(f"\n{'='*60}")
    print(f"  测试完成: {passed}/{total} 通过, {failed} 失败, {skipped} 跳过")
    print(f"  报告：{report_path}")
    print(f"  数据：{json_path}")
    print(f"{'='*60}")


def main():
    print(f"{'='*60}")
    print(f"  CDM System 基础功能测试")
    print(f"  时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}\n")

    test_django_setup()

    tests = [
        test_database,
        test_llm_api,
        test_llm_voice_parse,
        test_risk_assessment,
        test_rag_service,
        test_tts_dashscope,
        test_tts_edge,
        test_health_feedback,
        test_seed_command,
    ]

    for fn in tests:
        try:
            fn()
        except Exception:
            pass

    generate_report()


if __name__ == "__main__":
    main()
