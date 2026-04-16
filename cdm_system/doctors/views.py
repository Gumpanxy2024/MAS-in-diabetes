import json
from datetime import timedelta

from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.db.models import Count, Q

from accounts.decorators import doctor_required
from patients.models import Patient, HealthRecord
from risk.models import RiskRecord
from .models import Doctor, VisitTask, MedicationPlan
from .forms import PatientForm, MedicationPlanForm
from agents import medication_agent


# ─────────────────────── 工作台 ───────────────────────

@doctor_required
def dashboard(request):
    """医生工作台：汇总看板。"""
    doctor = request.user.doctor_profile
    patients = Patient.objects.filter(doctor=doctor, is_active=True)
    patient_ids = patients.values_list("pk", flat=True)

    red_count = RiskRecord.objects.filter(
        patient_id__in=patient_ids, risk_level="red"
    ).values("patient_id").distinct().count()

    yellow_count = RiskRecord.objects.filter(
        patient_id__in=patient_ids, risk_level="yellow"
    ).values("patient_id").distinct().count()

    today = timezone.now().date()
    overdue_visits = VisitTask.objects.filter(
        doctor=doctor, status="pending", due_date__lt=today
    ).count()
    upcoming_visits = VisitTask.objects.filter(
        doctor=doctor, status="pending",
        due_date__range=(today, today + timedelta(days=7)),
    ).count()

    refill_alerts = medication_agent.run_reminder_check()
    my_refill_alerts = [a for a in refill_alerts if a["patient_id"] in patient_ids]

    return render(request, "doctors/dashboard.html", {
        "doctor": doctor,
        "total_patients": patients.count(),
        "red_count": red_count,
        "yellow_count": yellow_count,
        "overdue_visits": overdue_visits,
        "upcoming_visits": upcoming_visits,
        "refill_alerts": my_refill_alerts,
    })


@doctor_required
def dashboard_stats_api(request):
    """AJAX接口：工作台统计数据（供图表刷新）。"""
    doctor = request.user.doctor_profile
    patient_ids = Patient.objects.filter(
        doctor=doctor, is_active=True
    ).values_list("pk", flat=True)

    risk_dist = (
        RiskRecord.objects
        .filter(patient_id__in=patient_ids)
        .values("risk_level")
        .annotate(count=Count("patient_id", distinct=True))
    )
    risk_map = {r["risk_level"]: r["count"] for r in risk_dist}

    return JsonResponse({
        "risk_distribution": {
            "red": risk_map.get("red", 0),
            "yellow": risk_map.get("yellow", 0),
            "green": risk_map.get("green", 0),
        },
    })


# ─────────────────────── 患者管理 ───────────────────────

@doctor_required
def patient_list(request):
    """患者列表，支持风险等级筛选和搜索。"""
    doctor = request.user.doctor_profile
    qs = Patient.objects.filter(doctor=doctor)

    q = request.GET.get("q", "").strip()
    if q:
        qs = qs.filter(Q(name__icontains=q) | Q(user__username__icontains=q))

    risk_filter = request.GET.get("risk", "")
    if risk_filter:
        risk_patient_ids = RiskRecord.objects.filter(
            risk_level=risk_filter
        ).values_list("patient_id", flat=True)
        qs = qs.filter(pk__in=risk_patient_ids)

    active_filter = request.GET.get("active", "")
    if active_filter == "1":
        qs = qs.filter(is_active=True)
    elif active_filter == "0":
        qs = qs.filter(is_active=False)

    patients_with_risk = []
    for p in qs.order_by("-created_at"):
        latest_risk = RiskRecord.objects.filter(patient=p).first()
        patients_with_risk.append({"patient": p, "latest_risk": latest_risk})

    return render(request, "doctors/patient_list.html", {
        "patients": patients_with_risk,
        "q": q,
        "risk_filter": risk_filter,
        "active_filter": active_filter,
    })


@doctor_required
def patient_detail(request, patient_id):
    """患者详情：基本信息 + 最近健康记录 + 风险历史 + 用药方案。"""
    doctor = request.user.doctor_profile
    patient = get_object_or_404(Patient, pk=patient_id, doctor=doctor)

    recent_records = HealthRecord.objects.filter(patient=patient)[:10]
    risk_records = RiskRecord.objects.filter(patient=patient)[:10]
    med_plans = MedicationPlan.objects.filter(patient=patient, is_active=True)
    visits = VisitTask.objects.filter(patient=patient).order_by("-created_at")[:10]
    adherence = medication_agent.calculate_adherence_rate(patient.pk, days=30)

    latest_risk = risk_records.first()
    ai_summary = ""
    if latest_risk:
        recent_summary_parts = []
        for r in recent_records[:5]:
            parts = []
            if r.fasting_glucose:
                parts.append(f"空腹{r.fasting_glucose}")
            if r.postmeal_glucose:
                parts.append(f"餐后{r.postmeal_glucose}")
            if parts:
                recent_summary_parts.append(f"{r.recorded_at.strftime('%m-%d')}:{'，'.join(parts)}")
        recent_text = "；".join(recent_summary_parts) if recent_summary_parts else "暂无近期数据"

        from agents.doctor_agent import generate_patient_summary
        ai_summary = generate_patient_summary(
            patient_name=patient.name,
            risk_level=latest_risk.risk_level,
            risk_score=float(latest_risk.risk_score),
            trigger_indicators=latest_risk.trigger_indicators or [],
            recent_records_summary=recent_text,
            adherence_rate=adherence,
            patient_id=patient.pk,
            user=request.user,
        )

    from agents.models import AgentLog
    agent_logs = AgentLog.objects.filter(patient=patient).order_by("-created_at")[:20]

    return render(request, "doctors/patient_detail.html", {
        "patient": patient,
        "recent_records": recent_records,
        "risk_records": risk_records,
        "med_plans": med_plans,
        "visits": visits,
        "adherence_rate": adherence,
        "ai_summary": ai_summary,
        "agent_logs": agent_logs,
    })


@doctor_required
def patient_create(request):
    """新增患者（创建User + Patient记录）。"""
    doctor = request.user.doctor_profile
    form = PatientForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        from accounts.models import User

        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")
        phone = request.POST.get("phone", "")

        if User.objects.filter(username=username).exists():
            form.add_error(None, "该用户名已存在")
        else:
            user = User.objects.create_user(
                username=username, password=password,
                role="patient", phone=phone,
            )
            patient = form.save(commit=False)
            patient.user = user
            patient.doctor = doctor
            patient.save()
            return redirect("doctor_patient_detail", patient_id=patient.pk)

    return render(request, "doctors/patient_form.html", {
        "form": form,
        "action": "新增",
    })


@doctor_required
def patient_edit(request, patient_id):
    """编辑患者信息。"""
    doctor = request.user.doctor_profile
    patient = get_object_or_404(Patient, pk=patient_id, doctor=doctor)
    form = PatientForm(request.POST or None, instance=patient)

    if request.method == "POST" and form.is_valid():
        form.save()
        return redirect("doctor_patient_detail", patient_id=patient.pk)

    return render(request, "doctors/patient_form.html", {
        "form": form,
        "action": "编辑",
        "patient": patient,
    })


@doctor_required
def patient_health_trend_api(request, patient_id):
    """AJAX接口：某患者的健康趋势数据。"""
    doctor = request.user.doctor_profile
    patient = get_object_or_404(Patient, pk=patient_id, doctor=doctor)
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


@doctor_required
def patient_risk_history_api(request, patient_id):
    """AJAX接口：某患者的风险评分历史。"""
    doctor = request.user.doctor_profile
    patient = get_object_or_404(Patient, pk=patient_id, doctor=doctor)
    days = int(request.GET.get("days", 90))
    cutoff = timezone.now() - timedelta(days=days)

    records = RiskRecord.objects.filter(
        patient=patient, evaluated_at__gte=cutoff
    ).order_by("evaluated_at").values(
        "evaluated_at", "risk_level", "risk_score", "trigger_indicators",
    )

    data = []
    for r in records:
        data.append({
            "date": r["evaluated_at"].strftime("%m-%d"),
            "risk_level": r["risk_level"],
            "risk_score": float(r["risk_score"]),
            "triggers": r["trigger_indicators"] or [],
        })
    return JsonResponse({"data": data})


# ─────────────────────── 风险预警 ───────────────────────

@doctor_required
def risk_alerts(request):
    """红/黄码患者预警列表。"""
    doctor = request.user.doctor_profile
    patient_ids = Patient.objects.filter(
        doctor=doctor, is_active=True
    ).values_list("pk", flat=True)

    level_filter = request.GET.get("level", "")
    qs = RiskRecord.objects.filter(
        patient_id__in=patient_ids,
        risk_level__in=["red", "yellow"],
    ).select_related("patient", "health_record")

    if level_filter in ("red", "yellow"):
        qs = qs.filter(risk_level=level_filter)

    seen_patients = set()
    alerts = []
    for r in qs.order_by("-evaluated_at"):
        if r.patient_id not in seen_patients:
            seen_patients.add(r.patient_id)
            alerts.append(r)

    return render(request, "doctors/risk_alerts.html", {
        "alerts": alerts,
        "level_filter": level_filter,
    })


# ─────────────────────── 随访管理 ───────────────────────

@doctor_required
def visit_list(request):
    """随访任务列表。"""
    doctor = request.user.doctor_profile
    status_filter = request.GET.get("status", "pending")
    qs = VisitTask.objects.filter(doctor=doctor).select_related("patient")

    if status_filter:
        qs = qs.filter(status=status_filter)

    return render(request, "doctors/visit_list.html", {
        "visits": qs,
        "status_filter": status_filter,
    })


@require_POST
@doctor_required
def visit_complete(request, visit_id):
    """标记随访任务已完成。"""
    doctor = request.user.doctor_profile
    visit = get_object_or_404(VisitTask, pk=visit_id, doctor=doctor)
    remark = request.POST.get("remark", "")

    visit.status = "completed"
    visit.completed_at = timezone.now()
    if remark:
        visit.remark = remark
    visit.save()

    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return JsonResponse({"success": True})
    return redirect("doctor_visits")


@require_POST
@doctor_required
def visit_defer(request, visit_id):
    """延期随访任务。"""
    doctor = request.user.doctor_profile
    visit = get_object_or_404(VisitTask, pk=visit_id, doctor=doctor)
    defer_days = int(request.POST.get("defer_days", 7))

    visit.status = "deferred"
    visit.due_date = visit.due_date + timedelta(days=defer_days)
    visit.remark += f"\n延期{defer_days}天"
    visit.save()

    VisitTask.objects.create(
        patient=visit.patient,
        doctor=doctor,
        visit_type=visit.visit_type,
        priority=visit.priority,
        due_date=visit.due_date,
        status="pending",
        remark=f"由延期任务#{visit.pk}生成",
    )

    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return JsonResponse({"success": True})
    return redirect("doctor_visits")


# ─────────────────────── 用药监控 ───────────────────────

@doctor_required
def medication_monitor(request):
    """用药监控面板：依从率 + 续方预警。"""
    doctor = request.user.doctor_profile
    patients = Patient.objects.filter(doctor=doctor, is_active=True)

    patient_med_data = []
    for p in patients:
        plans = MedicationPlan.objects.filter(patient=p, is_active=True)
        if not plans.exists():
            continue
        adherence = medication_agent.calculate_adherence_rate(p.pk, days=30)
        refill_list = [
            plan for plan in plans if plan.refill_needed
        ]
        patient_med_data.append({
            "patient": p,
            "adherence_rate": adherence,
            "plan_count": plans.count(),
            "refill_alerts": refill_list,
        })

    patient_med_data.sort(key=lambda x: x["adherence_rate"])

    return render(request, "doctors/medication_monitor.html", {
        "patient_med_data": patient_med_data,
    })


@doctor_required
def medication_plan_create(request, patient_id):
    """为患者新增用药方案。"""
    doctor = request.user.doctor_profile
    patient = get_object_or_404(Patient, pk=patient_id, doctor=doctor)
    form = MedicationPlanForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        plan = form.save(commit=False)
        plan.patient = patient
        plan.save()
        return redirect("doctor_patient_detail", patient_id=patient.pk)

    return render(request, "doctors/medication_plan_form.html", {
        "form": form,
        "patient": patient,
        "action": "新增",
    })


@doctor_required
def medication_plan_edit(request, plan_id):
    """编辑用药方案。"""
    doctor = request.user.doctor_profile
    plan = get_object_or_404(MedicationPlan, pk=plan_id, patient__doctor=doctor)
    form = MedicationPlanForm(request.POST or None, instance=plan)

    if request.method == "POST" and form.is_valid():
        form.save()
        return redirect("doctor_patient_detail", patient_id=plan.patient.pk)

    return render(request, "doctors/medication_plan_form.html", {
        "form": form,
        "patient": plan.patient,
        "action": "编辑",
    })


@doctor_required
def patient_adherence_api(request, patient_id):
    """AJAX接口：患者依从率趋势（按周）。"""
    doctor = request.user.doctor_profile
    patient = get_object_or_404(Patient, pk=patient_id, doctor=doctor)
    weeks = int(request.GET.get("weeks", 8))

    data = []
    today = timezone.now().date()
    for i in range(weeks - 1, -1, -1):
        start = today - timedelta(weeks=i + 1)
        end = today - timedelta(weeks=i)
        from patients.models import MedicationRecord
        total = MedicationRecord.objects.filter(
            patient=patient,
            scheduled_time__date__gte=start,
            scheduled_time__date__lt=end,
        ).count()
        taken = MedicationRecord.objects.filter(
            patient=patient,
            scheduled_time__date__gte=start,
            scheduled_time__date__lt=end,
            status="taken",
        ).count()
        rate = round((taken / total) * 100, 1) if total > 0 else 100.0
        data.append({
            "week": f"W{weeks - i}",
            "start": start.isoformat(),
            "end": end.isoformat(),
            "rate": rate,
        })

    return JsonResponse({"data": data})
