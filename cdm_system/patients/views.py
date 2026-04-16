import json
from datetime import timedelta

from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_POST

from accounts.decorators import patient_required
from .models import Patient, HealthRecord, MedicationRecord
from doctors.models import MedicationPlan, VisitTask
from risk.models import RiskRecord
from agents import medication_agent


@patient_required
def dashboard(request):
    """患者首页：风险状态 + 最近记录 + 下次随访 + 今日用药。"""
    patient = request.user.patient_profile

    latest_risk = RiskRecord.objects.filter(patient=patient).first()
    recent_records = HealthRecord.objects.filter(patient=patient)[:5]
    next_visit = VisitTask.objects.filter(
        patient=patient, status="pending"
    ).order_by("due_date").first()
    today_plans = MedicationPlan.objects.filter(patient=patient, is_active=True)

    return render(request, "patients/dashboard.html", {
        "patient": patient,
        "latest_risk": latest_risk,
        "recent_records": recent_records,
        "next_visit": next_visit,
        "today_plans": today_plans,
    })


@patient_required
def health_input(request):
    """健康数据录入页面（语音/文字双模式）。"""
    patient = request.user.patient_profile

    if request.method == "POST":
        input_type = request.POST.get("input_type", "text")
        raw_text = request.POST.get("voice_text", "")

        from agents.graph import app as agent_app

        if input_type == "voice":
            initial_state = {
                "patient_id": patient.pk,
                "patient_name": "",
                "raw_input": raw_text,
                "input_type": "voice",
                "health_record": {},
                "health_record_id": None,
                "risk_level": "",
                "risk_score": 0.0,
                "previous_risk_level": "",
                "trigger_indicators": [],
                "visit_task_id": None,
                "next_visit_date": None,
                "medication_alert": False,
                "flow_log": [],
            }
        else:
            health_data = {
                "fasting_glucose": request.POST.get("fasting_glucose") or None,
                "postmeal_glucose": request.POST.get("postmeal_glucose") or None,
                "systolic_bp": request.POST.get("systolic_bp") or None,
                "diastolic_bp": request.POST.get("diastolic_bp") or None,
                "weight": request.POST.get("weight") or None,
            }
            initial_state = {
                "patient_id": patient.pk,
                "patient_name": "",
                "raw_input": "",
                "input_type": "text",
                "health_record": health_data,
                "health_record_id": None,
                "risk_level": "",
                "risk_score": 0.0,
                "previous_risk_level": "",
                "trigger_indicators": [],
                "visit_task_id": None,
                "next_visit_date": None,
                "medication_alert": False,
                "flow_log": [],
            }

        result = agent_app.invoke(initial_state)

        from agents.patient_agent import generate_health_feedback
        feedback = generate_health_feedback(
            result.get("health_record", {}),
            result.get("risk_level", ""),
            patient_id=patient.pk,
            user=request.user,
        )

        request.session["last_result"] = {
            "risk_level": result.get("risk_level", ""),
            "risk_score": result.get("risk_score", 0),
            "triggers": result.get("trigger_indicators", []),
            "flow_log": result.get("flow_log", []),
            "health_feedback": feedback,
            "health_record_id": result.get("health_record_id"),
        }
        return redirect("patient_input_result")

    return render(request, "patients/health_input.html", {"patient": patient})


@patient_required
def health_input_result(request):
    """数据提交后的评估结果页。"""
    result = request.session.pop("last_result", {})
    return render(request, "patients/input_result.html", {"result": result})


@require_POST
@patient_required
def voice_parse_api(request):
    """AJAX接口：语音文本 → LLM解析 → 返回结构化JSON（不入库，仅预览）。"""
    body = json.loads(request.body)
    text = body.get("text", "")

    from agents.patient_agent import parse_voice_text, validate_health_data
    parsed = parse_voice_text(text)
    cleaned = validate_health_data(parsed)

    return JsonResponse({"success": True, "data": cleaned})


@require_POST
@patient_required
def voice_upload_api(request):
    """AJAX接口：接收录音文件 → 服务端 ASR 转写 → 返回文本。"""
    audio_file = request.FILES.get("audio")
    if not audio_file:
        return JsonResponse({"success": False, "error": "未收到音频文件"}, status=400)

    audio_bytes = audio_file.read()
    filename = audio_file.name or "recording.webm"

    from agents.speech_service import transcribe_audio
    result = transcribe_audio(audio_bytes, filename)

    patient = request.user.patient_profile
    if result.get("text"):
        from agents.patient_agent import _write_log
        _write_log(
            patient_id=patient.pk,
            log_type="asr",
            agent_name="SpeechService",
            raw_input=f"[audio:{filename}, {len(audio_bytes)} bytes]",
            raw_output=result["text"],
            duration_ms=result.get("duration_ms"),
            user=request.user,
        )

    return JsonResponse({
        "success": not result.get("error"),
        "text": result.get("text", ""),
        "duration_ms": result.get("duration_ms", 0),
        "provider": result.get("provider", ""),
        "error": result.get("error", ""),
    })


@require_POST
@patient_required
def tts_api(request):
    """AJAX接口：文本 → TTS 合成 → 返回音频文件 URL。"""
    body = json.loads(request.body)
    text = body.get("text", "")
    if not text:
        return JsonResponse({"success": False, "error": "文本为空"}, status=400)

    from agents.speech_service import synthesize_speech
    result = synthesize_speech(text)

    if result.get("audio_path"):
        from django.conf import settings as _settings
        audio_url = _settings.MEDIA_URL + result["audio_path"].replace("media/", "", 1).replace("media\\", "", 1)
        return JsonResponse({
            "success": True,
            "audio_url": audio_url,
            "duration_ms": result.get("duration_ms", 0),
        })
    else:
        return JsonResponse({
            "success": False,
            "error": result.get("error", "TTS 合成失败"),
        })


@require_POST
@patient_required
def chat_api(request):
    """AJAX接口：RAG 健康问答。患者提问 → 知识库检索 → LLM 生成回答。"""
    body = json.loads(request.body)
    question = body.get("question", "").strip()
    if not question:
        return JsonResponse({"success": False, "error": "问题不能为空"}, status=400)

    patient = request.user.patient_profile

    from agents.rag_service import retrieve, generate_with_context, PATIENT_SYSTEM_PROMPT

    docs = retrieve(question, audience="patient", top_k=3)
    if docs:
        answer = generate_with_context(question, docs, PATIENT_SYSTEM_PROMPT, max_tokens=400)
    else:
        answer = ""

    if not answer:
        answer = "抱歉，我暂时无法回答这个问题，建议您咨询您的责任医生。"

    from agents.patient_agent import _write_log
    _write_log(
        patient_id=patient.pk,
        log_type="rag_chat",
        agent_name="RAGService",
        raw_input=question,
        raw_output=answer,
        user=request.user,
    )

    return JsonResponse({
        "success": True,
        "answer": answer,
        "sources": [d["source"] for d in docs],
    })


@patient_required
def health_records(request):
    """健康记录历史 + 趋势图。"""
    patient = request.user.patient_profile
    days = int(request.GET.get("days", 30))
    cutoff = timezone.now() - timedelta(days=days)
    records = HealthRecord.objects.filter(
        patient=patient, recorded_at__gte=cutoff
    ).order_by("recorded_at")

    return render(request, "patients/health_records.html", {
        "patient": patient,
        "records": records,
        "days": days,
    })


@patient_required
def health_trend_api(request):
    """AJAX接口：返回血糖/血压趋势数据供前端图表渲染。"""
    patient = request.user.patient_profile
    days = int(request.GET.get("days", 30))
    cutoff = timezone.now() - timedelta(days=days)
    records = HealthRecord.objects.filter(
        patient=patient, recorded_at__gte=cutoff
    ).order_by("recorded_at").values(
        "recorded_at", "fasting_glucose", "postmeal_glucose",
        "systolic_bp", "diastolic_bp", "weight",
    )

    data = []
    for r in records:
        data.append({
            "date": r["recorded_at"].strftime("%m-%d"),
            "fasting_glucose": float(r["fasting_glucose"]) if r["fasting_glucose"] else None,
            "postmeal_glucose": float(r["postmeal_glucose"]) if r["postmeal_glucose"] else None,
            "systolic_bp": r["systolic_bp"],
            "diastolic_bp": r["diastolic_bp"],
            "weight": float(r["weight"]) if r["weight"] else None,
        })
    return JsonResponse({"data": data})


@patient_required
def medication_page(request):
    """用药管理页面：今日方案 + 打卡 + 依从率。"""
    patient = request.user.patient_profile
    plans = MedicationPlan.objects.filter(patient=patient, is_active=True)

    today = timezone.now().date()
    today_records = MedicationRecord.objects.filter(
        patient=patient,
        scheduled_time__date=today,
    )

    adherence = medication_agent.calculate_adherence_rate(patient.pk, days=30)

    return render(request, "patients/medication.html", {
        "patient": patient,
        "plans": plans,
        "today_records": today_records,
        "adherence_rate": adherence,
    })


@require_POST
@patient_required
def medication_checkin_api(request):
    """AJAX接口：用药打卡。"""
    body = json.loads(request.body)
    plan_id = body.get("plan_id")
    status = body.get("status", "taken")
    patient = request.user.patient_profile

    record = medication_agent.handle_checkin(plan_id, patient.pk, status)

    refill_needed = medication_agent.check_refill_needed(plan_id)

    return JsonResponse({
        "success": True,
        "record_id": record.pk,
        "refill_alert": refill_needed,
    })


@patient_required
def my_visits(request):
    """患者查看自己的随访安排。"""
    patient = request.user.patient_profile
    visits = VisitTask.objects.filter(patient=patient).order_by("-created_at")[:20]
    return render(request, "patients/my_visits.html", {
        "patient": patient,
        "visits": visits,
    })


@patient_required
def ai_history(request):
    """患者查看自己的 AI 交互历史（健康反馈、语音解析等）。"""
    patient = request.user.patient_profile
    from agents.models import AgentLog
    logs = AgentLog.objects.filter(
        patient=patient,
        log_type__in=["health_feedback", "voice_parse", "asr"],
    ).order_by("-created_at")[:30]
    return render(request, "patients/ai_history.html", {
        "patient": patient,
        "logs": logs,
    })
