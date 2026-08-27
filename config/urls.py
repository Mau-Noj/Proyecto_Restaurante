from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from config.views import healthz

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("apps.accounts.urls")),
    path("panel/", include("apps.dashboard.urls")),
    path("panel/personal/", include("apps.employees.urls")),
    path("mesas/", include("apps.tables.urls")),
    path("kds/", include("apps.kds.urls")),
    path("inventario/", include("apps.inventory.urls")),
    path("pagos/", include("apps.payments.urls")),
    path("catalogo/", include("apps.catalog.urls")),
    path("healthz/", healthz, name="healthz"),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
