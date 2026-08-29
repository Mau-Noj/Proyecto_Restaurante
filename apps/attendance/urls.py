from django.urls import path

from . import views

app_name = "attendance"

urlpatterns = [
    path("kioscos/", views.kiosk_list, name="kiosk_list"),
    path("kioscos/nuevo/", views.kiosk_create, name="kiosk_create"),
    path("kioscos/<int:kiosk_id>/", views.kiosk_display, name="kiosk_display"),
    path("kioscos/<int:kiosk_id>/qr.png", views.kiosk_qr_image, name="kiosk_qr_image"),
    path("marcar/", views.mark_confirm, name="mark_confirm"),
    path("mi-asistencia/", views.my_attendance, name="my_attendance"),
    path("marcaciones/<int:entry_id>/ajustar/", views.entry_adjust, name="entry_adjust"),
    path("reportes/horas/", views.report_hours, name="report_hours"),
]
