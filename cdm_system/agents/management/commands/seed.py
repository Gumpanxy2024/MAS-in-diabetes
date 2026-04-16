"""
seed 数据脚本 —— 一键创建开发演示所需的全量种子数据。

用法:
    python manage.py seed          # 创建种子数据（幂等，已存在则跳过）
    python manage.py seed --reset  # 清空后重新创建
"""
import random
from datetime import date, timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.utils import timezone

from accounts.models import User
from patients.models import Patient, HealthRecord, MedicationRecord
from doctors.models import Doctor, VisitTask, MedicationPlan
from risk.models import RiskRecord
from agents.models import AgentLog


class Command(BaseCommand):
    help = "创建开发演示用种子数据（患者、医生、健康记录、风险评估、用药方案、AgentLog等）"

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset",
            action="store_true",
            help="清空现有业务数据后重新创建",
        )

    def handle(self, *args, **options):
        if options["reset"]:
            self._clean()

        if User.objects.filter(username="doctor_zhang").exists():
            self.stdout.write(self.style.WARNING("种子数据已存在，跳过。如需重建请使用 --reset"))
            return

        doctor_user, doctor = self._create_doctor()
        patients = self._create_patients(doctor)
        self._create_health_records(patients)
        self._create_medication_plans(patients)
        self._create_visit_tasks(patients, doctor)
        self._create_agent_logs(patients)

        self.stdout.write(self.style.SUCCESS(
            f"种子数据创建完成: 1名医生, {len(patients)}名患者, "
            f"{HealthRecord.objects.count()}条健康记录, "
            f"{RiskRecord.objects.count()}条风险评估, "
            f"{MedicationPlan.objects.count()}个用药方案, "
            f"{VisitTask.objects.count()}条随访任务, "
            f"{AgentLog.objects.count()}条AgentLog"
        ))

    # ── 清理 ──────────────────────────────────────────
    def _clean(self):
        self.stdout.write("正在清理现有业务数据...")
        AgentLog.objects.all().delete()
        MedicationRecord.objects.all().delete()
        RiskRecord.objects.all().delete()
        VisitTask.objects.all().delete()
        MedicationPlan.objects.all().delete()
        HealthRecord.objects.all().delete()
        Patient.objects.all().delete()
        Doctor.objects.all().delete()
        User.objects.filter(username__startswith="doctor_").delete()
        User.objects.filter(username__startswith="patient_").delete()
        self.stdout.write(self.style.SUCCESS("清理完成"))

    # ── 医生 ──────────────────────────────────────────
    def _create_doctor(self):
        user = User.objects.create_user(
            username="doctor_zhang",
            password="demo1234",
            first_name="建国",
            last_name="张",
            role="doctor",
            phone="13800001111",
        )
        doctor = Doctor.objects.create(user=user, name="张建国")
        self.stdout.write(f"  医生: {doctor.name} (账号: doctor_zhang / demo1234)")
        return user, doctor

    # ── 患者 ──────────────────────────────────────────
    PATIENT_DATA = [
        {"username": "patient_li",  "pwd": "demo1234", "first": "淑芬", "last": "李", "name": "李淑芬", "age": 68, "gender": "女", "height": 158.0, "year": 2018},
        {"username": "patient_wang","pwd": "demo1234", "first": "德明", "last": "王", "name": "王德明", "age": 72, "gender": "男", "height": 170.5, "year": 2015},
        {"username": "patient_chen","pwd": "demo1234", "first": "秀英", "last": "陈", "name": "陈秀英", "age": 65, "gender": "女", "height": 155.0, "year": 2020},
        {"username": "patient_zhao","pwd": "demo1234", "first": "国强", "last": "赵", "name": "赵国强", "age": 75, "gender": "男", "height": 168.0, "year": 2012},
        {"username": "patient_liu", "pwd": "demo1234", "first": "玉兰", "last": "刘", "name": "刘玉兰", "age": 70, "gender": "女", "height": 160.0, "year": 2019},
    ]

    def _create_patients(self, doctor):
        patients = []
        for d in self.PATIENT_DATA:
            user = User.objects.create_user(
                username=d["username"],
                password=d["pwd"],
                first_name=d["first"],
                last_name=d["last"],
                role="patient",
                phone=f"138{random.randint(10000000, 99999999)}",
            )
            patient = Patient.objects.create(
                user=user,
                doctor=doctor,
                name=d["name"],
                age=d["age"],
                gender=d["gender"],
                height=Decimal(str(d["height"])),
                diagnosis_year=d["year"],
            )
            patients.append(patient)
            self.stdout.write(f"  患者: {patient.name} (账号: {d['username']} / {d['pwd']})")
        return patients

    # ── 健康记录 + 风险评估 ───────────────────────────
    def _create_health_records(self, patients):
        now = timezone.now()
        for patient in patients:
            for i in range(15):
                dt = now - timedelta(days=i * 2, hours=random.randint(6, 10))
                fpg = Decimal(str(round(random.uniform(4.5, 14.0), 1)))
                ppg = Decimal(str(round(random.uniform(6.0, 20.0), 1)))
                sbp = random.randint(110, 170)
                dbp = random.randint(60, 100)
                weight = Decimal(str(round(random.uniform(50.0, 85.0), 1)))
                hr = HealthRecord.objects.create(
                    patient=patient,
                    fasting_glucose=fpg,
                    postmeal_glucose=ppg,
                    systolic_bp=sbp,
                    diastolic_bp=dbp,
                    weight=weight,
                    input_type=random.choice(["voice", "text"]),
                )
                hr.recorded_at = dt
                hr.save(update_fields=["recorded_at"])

                risk_level, risk_score = self._calc_risk(fpg, ppg, sbp, dbp)
                triggers = []
                if fpg >= Decimal("7.0"):
                    triggers.append("空腹血糖偏高")
                if ppg >= Decimal("11.1"):
                    triggers.append("餐后血糖偏高")
                if sbp >= 140:
                    triggers.append("收缩压偏高")

                RiskRecord.objects.create(
                    patient=patient,
                    health_record=hr,
                    risk_level=risk_level,
                    risk_score=risk_score,
                    trigger_indicators=triggers if triggers else None,
                )

    @staticmethod
    def _calc_risk(fpg, ppg, sbp, dbp):
        score = Decimal("0")
        if fpg >= Decimal("10.0"):
            score += Decimal("0.4")
        elif fpg >= Decimal("7.0"):
            score += Decimal("0.2")
        if ppg >= Decimal("16.7"):
            score += Decimal("0.3")
        elif ppg >= Decimal("11.1"):
            score += Decimal("0.15")
        if sbp >= 160 or dbp >= 100:
            score += Decimal("0.2")
        elif sbp >= 140 or dbp >= 90:
            score += Decimal("0.1")

        if score >= Decimal("0.5"):
            return "red", min(score, Decimal("1.0"))
        elif score >= Decimal("0.2"):
            return "yellow", score
        return "green", score

    # ── 用药方案 + 打卡记录 ───────────────────────────
    MEDICATIONS = [
        {"drug": "二甲双胍缓释片", "dosage": "500mg", "freq": "每日2次", "times": "08:00,20:00", "days": 90},
        {"drug": "格列美脲片", "dosage": "2mg", "freq": "每日1次", "times": "08:00", "days": 60},
        {"drug": "阿卡波糖片", "dosage": "50mg", "freq": "每日3次", "times": "07:30,12:00,18:00", "days": 30},
    ]

    def _create_medication_plans(self, patients):
        for patient in patients:
            med = random.choice(self.MEDICATIONS)
            plan = MedicationPlan.objects.create(
                patient=patient,
                drug_name=med["drug"],
                dosage=med["dosage"],
                frequency=med["freq"],
                remind_times=med["times"],
                total_days=med["days"],
                start_date=date.today() - timedelta(days=random.randint(5, 30)),
            )
            now = timezone.now()
            for d in range(7):
                for t in med["times"].split(","):
                    h, m = t.split(":")
                    sched = (now - timedelta(days=d)).replace(hour=int(h), minute=int(m), second=0)
                    status = random.choices(["taken", "missed", "skipped"], weights=[80, 15, 5])[0]
                    checked = sched + timedelta(minutes=random.randint(0, 30)) if status == "taken" else None
                    MedicationRecord.objects.create(
                        plan=plan,
                        patient=patient,
                        scheduled_time=sched,
                        checked_at=checked,
                        status=status,
                    )

    # ── 随访任务 ──────────────────────────────────────
    def _create_visit_tasks(self, patients, doctor):
        for patient in patients:
            VisitTask.objects.create(
                patient=patient,
                doctor=doctor,
                visit_type=random.choice(["online", "offline", "home"]),
                priority="urgent" if patient.age >= 72 else "normal",
                due_date=date.today() + timedelta(days=random.randint(1, 14)),
                status="pending",
                remark="系统自动生成的随访任务（种子数据）",
            )

    # ── AgentLog 示例 ─────────────────────────────────
    def _create_agent_logs(self, patients):
        now = timezone.now()
        for patient in patients:
            AgentLog.objects.create(
                patient=patient,
                log_type="voice_parse",
                agent_name="PatientAgent",
                raw_input="今天早上空腹血糖七点二，餐后两小时十点五，血压一百三十五八十五",
                raw_output='{"fasting_glucose": 7.2, "postmeal_glucose": 10.5, "systolic_bp": 135, "diastolic_bp": 85}',
                created_by=patient.user,
                duration_ms=random.randint(800, 2500),
            )
            AgentLog.objects.create(
                patient=patient,
                log_type="risk_eval",
                agent_name="TriageAgent",
                raw_input='{"fpg": 7.2, "ppg": 10.5, "sbp": 135, "dbp": 85}',
                raw_output='{"risk_level": "yellow", "score": 0.2, "triggers": ["空腹血糖偏高"]}',
                created_by=patient.user,
                duration_ms=random.randint(50, 200),
            )
            AgentLog.objects.create(
                patient=patient,
                log_type="health_feedback",
                agent_name="PatientAgent",
                raw_input="基于最新健康记录生成RAG反馈",
                raw_output="您今日空腹血糖7.2mmol/L，略高于正常范围（3.9-6.1mmol/L）。根据《中国糖尿病防治指南》建议，请注意控制饮食中精制碳水的摄入量，增加膳食纤维。血压处于正常高值范围，建议继续保持低盐饮食。",
                created_by=patient.user,
                duration_ms=random.randint(3000, 6000),
            )
            AgentLog.objects.create(
                patient=patient,
                log_type="asr",
                agent_name="SpeechService",
                raw_input="[audio_file: recording_001.webm, 12.3秒]",
                raw_output="今天早上空腹血糖七点二，餐后两小时十点五，血压一百三十五八十五",
                created_by=patient.user,
                duration_ms=random.randint(1500, 3000),
            )
            for log in AgentLog.objects.filter(patient=patient):
                log.created_at = now - timedelta(hours=random.randint(1, 48))
                log.save(update_fields=["created_at"])
