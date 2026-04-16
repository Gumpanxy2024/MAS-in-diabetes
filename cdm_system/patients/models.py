from django.conf import settings
from django.db import models


class Patient(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="patient_profile",
        verbose_name="关联用户",
    )
    doctor = models.ForeignKey(
        "doctors.Doctor",
        on_delete=models.SET_NULL,
        null=True,
        related_name="patients",
        verbose_name="责任医生",
    )
    name = models.CharField("姓名", max_length=50)
    age = models.IntegerField("年龄")
    gender = models.CharField("性别", max_length=4, choices=[("男", "男"), ("女", "女")])
    height = models.DecimalField("身高(cm)", max_digits=4, decimal_places=1, null=True, blank=True)
    diagnosis_year = models.IntegerField("确诊年份")
    is_active = models.BooleanField("在管状态", default=True)
    created_at = models.DateTimeField("建档时间", auto_now_add=True)

    class Meta:
        verbose_name = "患者"
        verbose_name_plural = verbose_name

    def __str__(self):
        return f"{self.name}（{self.age}岁）"


class HealthRecord(models.Model):
    INPUT_TYPE_CHOICES = [
        ("voice", "语音录入"),
        ("text", "文字录入"),
    ]
    patient = models.ForeignKey(
        Patient,
        on_delete=models.CASCADE,
        related_name="health_records",
        verbose_name="所属患者",
    )
    fasting_glucose = models.DecimalField(
        "空腹血糖(mmol/L)", max_digits=4, decimal_places=1, null=True, blank=True
    )
    postmeal_glucose = models.DecimalField(
        "餐后2h血糖(mmol/L)", max_digits=4, decimal_places=1, null=True, blank=True
    )
    systolic_bp = models.IntegerField("收缩压(mmHg)", null=True, blank=True)
    diastolic_bp = models.IntegerField("舒张压(mmHg)", null=True, blank=True)
    weight = models.DecimalField("体重(kg)", max_digits=4, decimal_places=1, null=True, blank=True)
    input_type = models.CharField("录入方式", max_length=10, choices=INPUT_TYPE_CHOICES)
    recorded_at = models.DateTimeField("录入时间", auto_now_add=True)

    class Meta:
        verbose_name = "健康记录"
        verbose_name_plural = verbose_name
        ordering = ["-recorded_at"]

    def __str__(self):
        return f"{self.patient.name} - {self.recorded_at.strftime('%Y-%m-%d %H:%M')}"

    def get_recent(self, days=30):
        from django.utils import timezone
        from datetime import timedelta
        cutoff = timezone.now() - timedelta(days=days)
        return HealthRecord.objects.filter(
            patient=self.patient, recorded_at__gte=cutoff
        ).order_by("-recorded_at")


class MedicationRecord(models.Model):
    STATUS_CHOICES = [
        ("taken", "已服药"),
        ("missed", "漏服"),
        ("skipped", "跳过"),
    ]
    plan = models.ForeignKey(
        "doctors.MedicationPlan",
        on_delete=models.CASCADE,
        related_name="records",
        verbose_name="所属方案",
    )
    patient = models.ForeignKey(
        Patient,
        on_delete=models.CASCADE,
        related_name="medication_records",
        verbose_name="所属患者",
    )
    scheduled_time = models.DateTimeField("计划服药时间")
    checked_at = models.DateTimeField("实际打卡时间", null=True, blank=True)
    status = models.CharField("打卡状态", max_length=10, choices=STATUS_CHOICES)

    class Meta:
        verbose_name = "用药打卡记录"
        verbose_name_plural = verbose_name
        ordering = ["-scheduled_time"]

    def __str__(self):
        return f"{self.patient.name} - {self.plan.drug_name} - {self.get_status_display()}"
