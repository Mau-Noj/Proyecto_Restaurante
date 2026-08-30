from django.urls import path

from . import views

app_name = "attendance"

urlpatterns = [
    path("pantalla/", views.attendance_display, name="display"),
    path("pantalla/qr.png", views.kiosk_qr_image, name="kiosk_qr_image"),
    path(
        "pantalla/qr-entrada.png",
        views.kiosk_qr_static_entrada_image,
        name="kiosk_qr_static_entrada_image",
    ),
    path(
        "pantalla/qr-salida/<int:employee_id>.png",
        views.kiosk_qr_scoped_image,
        name="kiosk_qr_scoped_image",
    ),
    path("marcar/", views.mark_confirm, name="mark_confirm"),
    path("mi-asistencia/", views.my_attendance, name="my_attendance"),
    path("marcaciones/<int:entry_id>/ajustar/", views.entry_adjust, name="entry_adjust"),
    path("reportes/horas/", views.report_hours, name="report_hours"),
    path("pantalla/habilitar/", views.toggle_kiosk_access, name="toggle_kiosk_access"),
    path("turnos/", views.shift_list, name="shift_list"),
    path("turnos/nuevo/", views.shift_create, name="shift_create"),
    path(
        "turnos/<int:shift_id>/pedir-extra/",
        views.overtime_request_create,
        name="overtime_request_create",
    ),
    path("turnos/<int:shift_id>/proponer-extra/", views.overtime_propose, name="overtime_propose"),
    path(
        "horas-extra/<int:request_id>/responder/",
        views.overtime_respond,
        name="overtime_respond",
    ),
    path("horas-extra/<int:request_id>/decidir/", views.overtime_decide, name="overtime_decide"),
    path("horas-extra/", views.overtime_list, name="overtime_list"),
]
