from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages


def login_view(request):
    if request.user.is_authenticated:
        return redirect("role_router")

    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")
        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            return redirect("role_router")
        else:
            messages.error(request, "账号或密码错误，请重试")

    return render(request, "accounts/login.html")


@login_required
def logout_view(request):
    logout(request)
    return redirect("login")


@login_required
def role_router(request):
    """登录后根据角色跳转到对应首页。"""
    if request.user.is_doctor:
        return redirect("doctor_dashboard")
    elif request.user.is_patient:
        return redirect("patient_dashboard")
    else:
        return redirect("login")
