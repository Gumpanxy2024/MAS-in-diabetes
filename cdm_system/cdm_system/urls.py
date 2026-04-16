from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include

from accounts.views import role_router

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", role_router, name="role_router"),
    path("accounts/", include("accounts.urls")),
    path("patient/", include("patients.urls")),
    path("doctor/", include("doctors.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
