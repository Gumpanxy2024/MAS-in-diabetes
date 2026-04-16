from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """
    统一用户模型，通过 role 字段区分患者与医生。
    继承 AbstractUser 获得 Django 内置的密码哈希、Session 认证等安全机制。
    """
    ROLE_CHOICES = [
        ("patient", "患者"),
        ("doctor", "医生"),
    ]
    role = models.CharField("角色", max_length=10, choices=ROLE_CHOICES)
    phone = models.CharField("联系电话", max_length=20, blank=True, default="")

    class Meta:
        verbose_name = "系统用户"
        verbose_name_plural = verbose_name

    def __str__(self):
        return f"{self.get_full_name() or self.username} ({self.get_role_display()})"

    @property
    def is_patient(self):
        return self.role == "patient"

    @property
    def is_doctor(self):
        return self.role == "doctor"
