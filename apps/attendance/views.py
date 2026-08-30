from datetime import timedelta
from functools import wraps
from io import BytesIO

import qrcode
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.dateparse import parse_date
from django.utils.http import url_has_allowed_host_and_scheme

from apps.employees.decorators import position_required
from apps.employees.models import Employee

from .forms import AdjustmentForm, OvertimeRequestForm, OvertimeResponseForm, ShiftForm
from .models import Kiosk, KioskAccessRequest, OvertimeRequest, Shift, TimeEntry
from .services import (
    ClockError,
    clock_employee,
    clock_scoped,
    clock_static_entrada,
    create_adjustment,
    decide_overtime_request,
    employees_leaving_now,
    generate_kiosk_token,
    generate_scoped_token,
    get_default_kiosk,
    get_kiosk_access_status,
    kiosko_session_is_approved,
    next_entry_type,
    request_overtime,
    respond_kiosk_access_request,
    respond_overtime_proposal,
    static_entrada_token,
    worked_summary,
)

# Estas pantallas de administracion de asistencia (kioscos, turnos, horas
# extra) las puede usar tanto un admin/is_staff de Django como cualquier
# Employee con puesto Gerente -- son conceptos separados en este proyecto
# (is_staff no implica tener ficha de empleado, y viceversa), mismo criterio
# ya usado para el acceso al KDS.
gerente_required = position_required(Employee.Position.GERENTE)


def _can_view_kiosk_screen(user, session_key: str) -> bool:
    """Gerente/staff siempre puede (para poder revisar la pantalla sin
    tener que loguearse como Kiosko). La cuenta Kiosko puede si: el
    interruptor global está prendido (kiosk.enabled -- el admin dejó la
    pantalla sin fricción a propósito), o si ESTA sesión puntual de
    navegador ya fue aprobada por un Gerente/admin vía la alerta "¿sos
    vos?" (kiosko_session_is_approved) -- un "sí" no deja la puerta
    abierta para siempre, solo para quien la pidió en ese momento."""
    if not user.is_authenticated:
        return False
    if user.is_staff or user.is_superuser:
        return True
    employee = getattr(user, "employee_profile", None)
    if not employee:
        return False
    if employee.position == Employee.Position.GERENTE:
        return True
    if employee.position == Employee.Position.KIOSKO:
        if get_default_kiosk().enabled:
            return True
        return kiosko_session_is_approved(user, session_key)
    return False


def kiosko_access_required(view_func):
    """La pantalla de asistencia (y sus QR) ya NO es publica: hace falta
    una cuenta con puesto Kiosko (que el admin crea y controla como
    cualquier empleado) Y que esa sesión puntual haya sido autorizada
    (interruptor global, o aprobación puntual vía la alerta "¿sos vos?")
    -- así, aunque alguien consiga la contraseña de Kiosko, no puede
    usarla para abrir la pantalla desde fuera del local sin que un
    Gerente/admin lo apruebe."""

    @wraps(view_func)
    @login_required(login_url="accounts:login_empleado")
    def wrapped(request, *args, **kwargs):
        if not _can_view_kiosk_screen(request.user, request.session.session_key or ""):
            return render(
                request,
                "attendance/display_disabled.html",
                status=403,
            )
        return view_func(request, *args, **kwargs)

    return wrapped


# --- Pantalla de asistencia (requiere la cuenta Kiosko + que el admin -----
# --- la haya habilitado; ver kiosko_access_required) ------------------------


@login_required(login_url="accounts:login_empleado")
def attendance_display(request):
    """Un solo QR de entrada (fijo) + una tarjeta por cada empleado que le
    toca salir ahora, con su nombre y su propio QR.

    Si quien entra es la cuenta Kiosko pero la pantalla todavía no está
    habilitada, en vez de un simple "acceso denegado" dispara una
    solicitud en vivo ("¿sos vos?") que cualquier Gerente/admin conectado
    ve como alerta, y muestra una pantalla de espera mientras tanto (ver
    kiosk_waiting.html)."""
    session_key = request.session.session_key or ""
    if _can_view_kiosk_screen(request.user, session_key):
        kiosk = get_default_kiosk()
        leaving = employees_leaving_now()
        return render(
            request, "attendance/attendance_display.html", {"kiosk": kiosk, "leaving": leaving}
        )

    employee = getattr(request.user, "employee_profile", None)
    if not employee or employee.position != Employee.Position.KIOSKO:
        return render(request, "attendance/display_disabled.html", status=403)

    if not session_key:
        request.session.save()
        session_key = request.session.session_key

    access_request = get_kiosk_access_status(request.user, session_key)
    return render(
        request, "attendance/kiosk_waiting.html", {"access_request": access_request}
    )


@gerente_required
def kiosk_access_respond(request, request_id):
    access_request = get_object_or_404(
        KioskAccessRequest, pk=request_id, status=KioskAccessRequest.Status.PENDIENTE
    )
    if request.method == "POST":
        approved = request.POST.get("action") == "aprobar"
        respond_kiosk_access_request(access_request, request.user, approved)
        messages.success(
            request,
            "Acceso al kiosco aprobado." if approved else "Acceso al kiosco denegado.",
        )
    next_url = request.POST.get("next") or request.META.get("HTTP_REFERER")
    if next_url and url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
        return redirect(next_url)
    return redirect(reverse("dashboard:index"))


def _qr_response(url: str) -> HttpResponse:
    image = qrcode.make(url)
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    response = HttpResponse(buffer.getvalue(), content_type="image/png")
    response["Cache-Control"] = "no-store"
    return response


@kiosko_access_required
def kiosk_qr_image(request):
    kiosk = get_default_kiosk()
    token = generate_kiosk_token(kiosk)
    url = request.build_absolute_uri(
        reverse("attendance:mark_confirm") + f"?k={kiosk.pk}&mode=generico&t={token}"
    )
    return _qr_response(url)


@kiosko_access_required
def kiosk_qr_static_entrada_image(request):
    kiosk = get_default_kiosk()
    token = static_entrada_token(kiosk)
    url = request.build_absolute_uri(
        reverse("attendance:mark_confirm") + f"?k={kiosk.pk}&mode=entrada&t={token}"
    )
    return _qr_response(url)


@kiosko_access_required
def kiosk_qr_scoped_image(request, employee_id):
    kiosk = get_default_kiosk()
    employee = get_object_or_404(Employee, pk=employee_id)
    token = generate_scoped_token(kiosk, employee)
    url = request.build_absolute_uri(
        reverse("attendance:mark_confirm") + f"?k={kiosk.pk}&mode=salida&e={employee.pk}&t={token}"
    )
    return _qr_response(url)


# --- Marcar (escaneado desde el celular del empleado) -----------------------


@login_required(login_url="accounts:login_empleado")
def mark_confirm(request):
    params = request.GET if request.method == "GET" else request.POST
    kiosk_id = params.get("k")
    mode = params.get("mode", "generico")
    token = params.get("t")
    owner_id = params.get("e")

    employee = getattr(request.user, "employee_profile", None)
    if not employee:
        return render(
            request,
            "attendance/mark_error.html",
            {"message": "Tu cuenta no tiene ficha de empleado. Contacta al administrador."},
        )

    kiosk = Kiosk.objects.filter(pk=kiosk_id).first() if kiosk_id else None
    if not kiosk or not token:
        return render(
            request,
            "attendance/mark_error.html",
            {"message": "Código inválido. Escanea el QR del kiosco de nuevo."},
        )

    owner_employee = None
    if mode == "salida":
        owner_employee = Employee.objects.filter(pk=owner_id).select_related("user").first()
        if not owner_employee:
            return render(
                request, "attendance/mark_error.html", {"message": "Código inválido."}
            )
        if owner_employee.pk != employee.pk:
            owner_name = owner_employee.user.get_full_name() or owner_employee.user.username
            return render(
                request,
                "attendance/mark_error.html",
                {"message": f"Este código es para {owner_name}, no para vos."},
            )

    if request.method == "POST":
        try:
            if mode == "entrada":
                entry = clock_static_entrada(employee, kiosk, token)
            elif mode == "salida":
                entry = clock_scoped(employee, kiosk, token, owner_employee)
            else:
                entry = clock_employee(employee, kiosk, token)
        except ClockError as exc:
            return render(request, "attendance/mark_error.html", {"message": str(exc)})
        return render(request, "attendance/mark_success.html", {"entry": entry})

    if mode == "entrada":
        preview_type = TimeEntry.EntryType.ENTRADA
    elif mode == "salida":
        preview_type = TimeEntry.EntryType.SALIDA
    else:
        preview_type = next_entry_type(employee)

    return render(
        request,
        "attendance/mark_confirm.html",
        {
            "kiosk": kiosk,
            "mode": mode,
            "token": token,
            "owner_id": owner_id,
            "employee": employee,
            "preview_type": preview_type,
        },
    )


# --- Vista del empleado -------------------------------------------------------


@login_required(login_url="accounts:login_empleado")
def my_attendance(request):
    employee = getattr(request.user, "employee_profile", None)
    if not employee:
        return render(
            request,
            "attendance/mark_error.html",
            {"message": "Tu cuenta no tiene ficha de empleado."},
        )

    today = timezone.localdate()
    date_from = today - timedelta(days=30)
    entries = (
        TimeEntry.objects.filter(employee=employee, timestamp__date__gte=date_from)
        .prefetch_related("adjustments__adjusted_by")
        .order_by("-timestamp")
    )
    summary = worked_summary(employee, date_from, today)
    total_hours = round(sum(row["hours"] for row in summary), 2)

    today_shift = Shift.objects.filter(employee=employee, date=today).prefetch_related(
        "overtime_requests"
    ).first()
    pending_proposals = OvertimeRequest.objects.filter(
        employee=employee, origin=OvertimeRequest.Origin.ADMIN, status=OvertimeRequest.Status.PENDIENTE
    ).select_related("shift", "requested_by")
    my_requests = OvertimeRequest.objects.filter(employee=employee).select_related(
        "shift", "requested_by", "responded_by"
    )[:10]

    return render(
        request,
        "attendance/my_attendance.html",
        {
            "entries": entries,
            "summary": summary,
            "total_hours": total_hours,
            "date_from": date_from,
            "date_to": today,
            "today_shift": today_shift,
            "pending_proposals": pending_proposals,
            "my_requests": my_requests,
            "overtime_form": OvertimeRequestForm(),
            "response_form": OvertimeResponseForm(),
        },
    )


@gerente_required
def entry_adjust(request, entry_id):
    entry = get_object_or_404(TimeEntry, pk=entry_id)
    if request.method == "POST":
        form = AdjustmentForm(request.POST)
        if form.is_valid():
            create_adjustment(
                entry, request.user, form.cleaned_data["reason"], form.cleaned_data["new_timestamp"]
            )
            messages.success(request, "Ajuste registrado. El empleado lo verá en su historial.")
            return redirect(reverse("attendance:report_hours"))
    else:
        form = AdjustmentForm(initial={"new_timestamp": timezone.localtime(entry.timestamp)})
    return render(request, "attendance/entry_adjust.html", {"form": form, "entry": entry})


@gerente_required
def toggle_kiosk_access(request):
    kiosk = get_default_kiosk()
    if request.method == "POST":
        kiosk.enabled = not kiosk.enabled
        kiosk.save(update_fields=["enabled"])
        messages.success(
            request,
            "Pantalla de asistencia habilitada." if kiosk.enabled else "Pantalla de asistencia deshabilitada.",
        )
    return redirect(reverse("attendance:report_hours"))


@gerente_required
def report_hours(request):
    kiosk = get_default_kiosk()
    hasta = parse_date(request.GET.get("hasta", "")) or timezone.localdate()
    desde = parse_date(request.GET.get("desde", "")) or hasta - timedelta(days=30)

    rows = []
    for employee in Employee.objects.select_related("user"):
        summary = worked_summary(employee, desde, hasta)
        if not summary:
            continue
        rows.append(
            {
                "employee": employee,
                "days": len(summary),
                "regular": round(sum(r["regular"] for r in summary), 2),
                "overtime": round(sum(r["overtime"] for r in summary), 2),
                "unauthorized": round(sum(r["unauthorized"] for r in summary), 2),
                "no_shift": round(sum(r["no_shift"] for r in summary), 2),
                "hours": round(sum(r["hours"] for r in summary), 2),
                "daily": summary,
            }
        )
    rows.sort(key=lambda row: -row["hours"])

    recent_entries = (
        TimeEntry.objects.filter(timestamp__date__gte=desde, timestamp__date__lte=hasta)
        .select_related("employee__user", "kiosk")
        .order_by("-timestamp")[:100]
    )

    return render(
        request,
        "attendance/report_hours.html",
        {
            "kiosk": kiosk,
            "rows": rows,
            "recent_entries": recent_entries,
            "desde": desde,
            "hasta": hasta,
            "chart_labels": [
                row["employee"].user.get_full_name() or row["employee"].user.username for row in rows
            ],
            "chart_regular": [row["regular"] for row in rows],
            "chart_overtime": [row["overtime"] for row in rows],
        },
    )


# --- Turnos --------------------------------------------------------------------


@gerente_required
def shift_list(request):
    today = timezone.localdate()
    shifts = (
        Shift.objects.filter(date__gte=today - timedelta(days=1))
        .select_related("employee__user")
        .prefetch_related("overtime_requests")
        .order_by("date", "start_time")[:100]
    )
    return render(request, "attendance/shift_list.html", {"shifts": shifts, "today": today})


@gerente_required
def shift_create(request):
    if request.method == "POST":
        form = ShiftForm(request.POST)
        if form.is_valid():
            shift = form.save(commit=False)
            shift.created_by = request.user
            try:
                shift.save()
            except IntegrityError:
                messages.error(
                    request, "Ese empleado ya tiene un turno asignado ese día. Editalo en vez de duplicarlo."
                )
                return render(request, "attendance/shift_form.html", {"form": form})
            messages.success(request, "Turno asignado.")
            return redirect(reverse("attendance:shift_list"))
    else:
        form = ShiftForm()
    return render(request, "attendance/shift_form.html", {"form": form})


# --- Horas extra -----------------------------------------------------------------


@login_required(login_url="accounts:login_empleado")
def overtime_request_create(request, shift_id):
    employee = getattr(request.user, "employee_profile", None)
    shift = get_object_or_404(Shift, pk=shift_id, employee=employee)
    if request.method == "POST":
        form = OvertimeRequestForm(request.POST)
        if form.is_valid():
            request_overtime(
                shift,
                request.user,
                OvertimeRequest.Origin.EMPLEADO,
                form.cleaned_data["minutes"],
                form.cleaned_data["note"],
            )
            messages.success(request, "Solicitud enviada. Un gerente tiene que aprobarla.")
        else:
            for field in form:
                for error in field.errors:
                    messages.error(request, f"{field.label}: {error}")
    return redirect(reverse("attendance:my_attendance"))


@gerente_required
def overtime_propose(request, shift_id):
    shift = get_object_or_404(Shift, pk=shift_id)
    if request.method == "POST":
        form = OvertimeRequestForm(request.POST)
        if form.is_valid():
            request_overtime(
                shift,
                request.user,
                OvertimeRequest.Origin.ADMIN,
                form.cleaned_data["minutes"],
                form.cleaned_data["note"],
            )
            messages.success(request, "Propuesta enviada al empleado.")
        else:
            for field in form:
                for error in field.errors:
                    messages.error(request, f"{field.label}: {error}")
    return redirect(reverse("attendance:shift_list"))


@login_required(login_url="accounts:login_empleado")
def overtime_respond(request, request_id):
    employee = getattr(request.user, "employee_profile", None)
    overtime = get_object_or_404(
        OvertimeRequest, pk=request_id, employee=employee, origin=OvertimeRequest.Origin.ADMIN
    )
    if request.method == "POST":
        action = request.POST.get("action")
        try:
            if action == "rechazar":
                respond_overtime_proposal(overtime, request.user, 0)
                messages.success(request, "Propuesta rechazada.")
            else:
                form = OvertimeResponseForm(request.POST)
                if form.is_valid():
                    respond_overtime_proposal(
                        overtime, request.user, form.cleaned_data["accepted_minutes"]
                    )
                    messages.success(request, "Respuesta registrada.")
                else:
                    for field in form:
                        for error in field.errors:
                            messages.error(request, f"{field.label}: {error}")
        except ClockError as exc:
            messages.error(request, str(exc))
    return redirect(reverse("attendance:my_attendance"))


@gerente_required
def overtime_decide(request, request_id):
    overtime = get_object_or_404(OvertimeRequest, pk=request_id)
    if request.method == "POST":
        action = request.POST.get("action")
        try:
            if action == "aprobar":
                decide_overtime_request(overtime, request.user, True, overtime.requested_minutes)
                messages.success(request, "Solicitud aprobada.")
            else:
                decide_overtime_request(overtime, request.user, False)
                messages.success(request, "Solicitud rechazada.")
        except ClockError as exc:
            messages.error(request, str(exc))
    return redirect(reverse("attendance:overtime_list"))


@gerente_required
def overtime_list(request):
    pending = (
        OvertimeRequest.objects.filter(status=OvertimeRequest.Status.PENDIENTE)
        .select_related("employee__user", "shift", "requested_by")
        .order_by("created_at")
    )
    history = (
        OvertimeRequest.objects.exclude(status=OvertimeRequest.Status.PENDIENTE)
        .select_related("employee__user", "shift", "responded_by")
        .order_by("-responded_at")[:50]
    )
    return render(
        request, "attendance/overtime_list.html", {"pending": pending, "history": history}
    )
