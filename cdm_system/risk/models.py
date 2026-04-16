from django.db import models


class RiskRecord(models.Model):
    RISK_LEVEL_CHOICES = [
        ("green", "绿码（正常）"),
        ("yellow", "黄码（警示）"),
        ("red", "红码（危险）"),
    ]

    patient = models.ForeignKey(
        "patients.Patient",
        on_delete=models.CASCADE,
        related_name="risk_records",
        verbose_name="所属患者",
    )
    health_record = models.OneToOneField(
        "patients.HealthRecord",
        on_delete=models.CASCADE,
        related_name="risk_record",
        verbose_name="关联健康记录",
    )
    risk_level = models.CharField("风险等级", max_length=10, choices=RISK_LEVEL_CHOICES)
    risk_score = models.DecimalField("加权评分", max_digits=3, decimal_places=2)
    trigger_indicators = models.JSONField("异常指标", null=True, blank=True)
    evaluated_at = models.DateTimeField("评估时间", auto_now_add=True)

    class Meta:
        verbose_name = "风险评估记录"
        verbose_name_plural = verbose_name
        ordering = ["-evaluated_at"]

    def __str__(self):
        return f"{self.patient.name} - {self.get_risk_level_display()} ({self.risk_score})"
