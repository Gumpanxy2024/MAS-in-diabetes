from django.conf import settings
from django.db import models


class AgentLog(models.Model):
    """Agent 交互日志 — 记录每次 AI 参与的完整输入、输出与上下文。"""

    LOG_TYPE_CHOICES = [
        ("voice_parse", "语音解析"),
        ("health_feedback", "健康反馈"),
        ("doctor_summary", "诊疗摘要"),
        ("risk_eval", "风险评估"),
        ("asr", "语音识别"),
        ("tts", "语音合成"),
        ("flow", "流程流转"),
    ]

    patient = models.ForeignKey(
        "patients.Patient",
        on_delete=models.CASCADE,
        related_name="agent_logs",
        verbose_name="所属患者",
    )
    log_type = models.CharField("日志类型", max_length=20, choices=LOG_TYPE_CHOICES)
    agent_name = models.CharField("Agent名称", max_length=30)
    raw_input = models.TextField("原始输入", blank=True, default="")
    raw_output = models.TextField("原始输出", blank=True, default="")
    context_snapshot = models.JSONField("上下文快照", null=True, blank=True)
    health_record = models.ForeignKey(
        "patients.HealthRecord",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="agent_logs",
        verbose_name="关联健康记录",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="操作用户",
    )
    duration_ms = models.IntegerField("耗时(ms)", null=True, blank=True)
    created_at = models.DateTimeField("创建时间", auto_now_add=True)

    class Meta:
        verbose_name = "Agent交互日志"
        verbose_name_plural = verbose_name
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["patient", "-created_at"]),
            models.Index(fields=["log_type", "-created_at"]),
        ]

    def __str__(self):
        return f"{self.patient} | {self.get_log_type_display()} | {self.agent_name} | {self.created_at:%m-%d %H:%M}"
