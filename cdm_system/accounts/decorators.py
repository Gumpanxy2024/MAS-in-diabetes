from functools import wraps

from django.shortcuts import redirect
from django.contrib.auth.decorators import login_required


def patient_required(view_func):
    """仅允许患者角色访问。"""
    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        if not request.user.is_patient:
            return redirect("doctor_dashboard")
        return view_func(request, *args, **kwargs)
    return wrapper


def doctor_required(view_func):
    """仅允许医生角色访问。"""
    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        if not request.user.is_doctor:
            return redirect("patient_dashboard")
        return view_func(request, *args, **kwargs)
    return wrapper
