from django.contrib import admin
from django.urls import include, path

from config.views import healthz

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("apps.accounts.urls")),
    path("panel/", include("apps.dashboard.urls")),
    path("panel/personal/", include("apps.employees.urls")),
    path("healthz/", healthz, name="healthz"),
]
