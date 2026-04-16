from django.conf import settings
from django.db import models


class Doctor(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="doctor_profile",
        verbose_name="关联用户",
    )
    name = models.CharField("姓名", max_length=50)
    created_at = models.DateTimeField("创建时间", auto_now_add=True)

    class Meta:
        verbose_name = "医生"
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.name


class VisitTask(models.Model):
    VISIT_TYPE_CHOICES = [
        ("online", "线上轻问诊"),
        ("offline", "线下门诊"),
        ("home", "上门巡诊"),
    ]
    PRIORITY_CHOICES = [
        ("normal", "普通"),
        ("urgent", "紧急"),
    ]
    STATUS_CHOICES = [
        ("pending", "待处理"),
        ("completed", "已完成"),
        ("deferred", "已延期"),
    ]

    patient = models.ForeignKey(
        "patients.Patient",
        on_delete=models.CASCADE,
        related_name="visit_tasks",
        verbose_name="所属患者",
    )
    doctor = models.ForeignKey(
        Doctor,
        on_delete=models.CASCADE,
        related_name="visit_tasks",
        verbose_name="负责医生",
    )
    visit_type = models.CharField("随访方式", max_length=20, choices=VISIT_TYPE_CHOICES)
    priority = models.CharField("优先级", max_length=10, choices=PRIORITY_CHOICES, default="normal")
    due_date = models.DateField("截止日期")
    status = models.CharField("任务状态", max_length=20, choices=STATUS_CHOICES, default="pending")
    remark = models.TextField("随访备注", blank=True, default="")
    created_at = models.DateTimeField("创建时间", auto_now_add=True)
    completed_at = models.DateTimeField("完成时间", null=True, blank=True)

    class Meta:
        verbose_name = "随访任务"
        verbose_name_plural = verbose_name
        ordering = ["-priority", "due_date"]

    def __str__(self):
        return f"{self.patient.name} - {self.get_visit_type_display()} ({self.get_status_display()})"


class MedicationPlan(models.Model):
    patient = models.ForeignKey(
        "patients.Patient",
        on_delete=models.CASCADE,
        related_name="medication_plans",
        verbose_name="所属患者",
    )
    drug_name = models.CharField("药品名称", max_length=100)
    dosage = models.CharField("剂量", max_length=50)
    frequency = models.CharField("每日服药频次", max_length=20)
    remind_times = models.CharField("提醒时间", max_length=100, help_text="逗号分隔，如 08:00,20:00")
    total_days = models.IntegerField("处方总天数")
    start_date = models.DateField("方案起始日期")
    is_active = models.BooleanField("是否生效", default=True)
    created_at = models.DateTimeField("创建时间", auto_now_add=True)

    class Meta:
        verbose_name = "用药方案"
        verbose_name_plural = verbose_name

    def __str__(self):
        return f"{self.patient.name} - {self.drug_name} {self.dosage}"

    @property
    def remaining_days(self):
        from django.utils import timezone
        from datetime import timedelta
        end_date = self.start_date + timedelta(days=self.total_days)
        delta = end_date - timezone.now().date()
        return max(delta.days, 0)

    @property
    def refill_needed(self):
        REFILL_THRESHOLD = 3
        return self.is_active and self.remaining_days <= REFILL_THRESHOLD
