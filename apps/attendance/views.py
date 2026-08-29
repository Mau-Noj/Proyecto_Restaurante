from datetime import timedelta
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

from apps.accounts.decorators import staff_required
from apps.employees.models import Employee

from .forms import AdjustmentForm, KioskForm, OvertimeRequestForm, OvertimeResponseForm, ShiftForm
from .models import Kiosk, OvertimeRequest, Shift, TimeEntry
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
    next_entry_type,
    request_overtime,
    respond_overtime_proposal,
    static_entrada_token,
    worked_summary,
)

# --- Kioscos -----------------------------------------------------------------


@staff_required
def kiosk_list(request):
    kiosks = Kiosk.objects.all()
    return render(request, "attendance/kiosk_list.html", {"kiosks": kiosks})


@staff_required
def kiosk_create(request):
    if request.method == "POST":
        form = KioskForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Kiosco creado.")
            return redirect(reverse("attendance:kiosk_list"))
    else:
        form = KioskForm()
    return render(request, "attendance/kiosk_form.html", {"form": form})


@staff_required
def kiosk_display(request, kiosk_id):
    kiosk = get_object_or_404(Kiosk, pk=kiosk_id)
    leaving = employees_leaving_now()
    return render(
        request, "attendance/kiosk_display.html", {"kiosk": kiosk, "leaving": leaving}
    )


def _qr_response(url: str) -> HttpResponse:
    image = qrcode.make(url)
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    response = HttpResponse(buffer.getvalue(), content_type="image/png")
    response["Cache-Control"] = "no-store"
    return response


@staff_required
def kiosk_qr_image(request, kiosk_id):
    kiosk = get_object_or_404(Kiosk, pk=kiosk_id)
    token = generate_kiosk_token(kiosk)
    url = request.build_absolute_uri(
        reverse("attendance:mark_confirm") + f"?k={kiosk.pk}&mode=generico&t={token}"
    )
    return _qr_response(url)


@staff_required
def kiosk_qr_static_entrada_image(request, kiosk_id):
    kiosk = get_object_or_404(Kiosk, pk=kiosk_id)
    token = static_entrada_token(kiosk)
    url = request.build_absolute_uri(
        reverse("attendance:mark_confirm") + f"?k={kiosk.pk}&mode=entrada&t={token}"
    )
    return _qr_response(url)


@staff_required
def kiosk_qr_scoped_image(request, kiosk_id, employee_id):
    kiosk = get_object_or_404(Kiosk, pk=kiosk_id)
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


@staff_required
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


@staff_required
def report_hours(request):
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


@staff_required
def shift_list(request):
    today = timezone.localdate()
    shifts = (
        Shift.objects.filter(date__gte=today - timedelta(days=1))
        .select_related("employee__user")
        .prefetch_related("overtime_requests")
        .order_by("date", "start_time")[:100]
    )
    return render(request, "attendance/shift_list.html", {"shifts": shifts, "today": today})


@staff_required
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


@staff_required
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


@staff_required
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


@staff_required
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
