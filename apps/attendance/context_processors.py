from django.utils import timezone

from apps.employees.models import Employee

from .models import OvertimeRequest, Shift, TimeEntry
from .services import effective_shift_end, next_entry_type

ALERT_WINDOW_MINUTES = 15


def shift_alert(request):
    """Aviso "tu turno termina en X minutos" para la barra superior de
    empleados. Sin infraestructura de notificaciones push: solo se ve si la
    persona tiene la página abierta en ese momento (confiable en pantallas
    siempre-abiertas como el KDS; menos confiable en el celular de un
    mesero/cajero que no esté mirando la app justo entonces)."""
    user = getattr(request, "user", None)
    if not user or not user.is_authenticated:
        return {}
    employee = getattr(user, "employee_profile", None)
    if not employee:
        return {}

    today = timezone.localdate()
    shift = Shift.objects.filter(employee=employee, date=today).prefetch_related(
        "overtime_requests"
    ).first()
    if not shift or next_entry_type(employee) != TimeEntry.EntryType.SALIDA:
        return {}

    end = effective_shift_end(shift)
    now = timezone.now()
    minutes_left = (end - now).total_seconds() / 60
    if minutes_left > ALERT_WINDOW_MINUTES:
        return {}
    return {
        "shift_alert": {
            "minutes_left": round(minutes_left),
            "ended": minutes_left <= 0,
        }
    }


def pending_overtime_alert(request):
    """Aviso inmediato para el admin/Gerente de que hay solicitudes de
    horas extra esperando su aprobación, sin que tenga que entrar a la
    pantalla de Horas Extra para enterarse. Mismo criterio de acceso que
    las pantallas de administración de asistencia: is_staff o Gerente."""
    user = getattr(request, "user", None)
    if not user or not user.is_authenticated:
        return {}
    employee = getattr(user, "employee_profile", None)
    is_gerente = employee and employee.position == Employee.Position.GERENTE
    if not (user.is_staff or user.is_superuser or is_gerente):
        return {}

    count = OvertimeRequest.objects.filter(
        origin=OvertimeRequest.Origin.EMPLEADO, status=OvertimeRequest.Status.PENDIENTE
    ).count()
    if not count:
        return {}
    return {"pending_overtime_count": count}
