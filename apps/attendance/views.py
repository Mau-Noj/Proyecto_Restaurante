from datetime import timedelta
from io import BytesIO

import qrcode
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.dateparse import parse_date

from apps.accounts.decorators import staff_required
from apps.employees.models import Employee

from .forms import AdjustmentForm, KioskForm
from .models import Kiosk, TimeEntry
from .services import (
    ClockError,
    clock_employee,
    create_adjustment,
    generate_kiosk_token,
    next_entry_type,
    worked_summary,
)


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
    return render(request, "attendance/kiosk_display.html", {"kiosk": kiosk})


@staff_required
def kiosk_qr_image(request, kiosk_id):
    kiosk = get_object_or_404(Kiosk, pk=kiosk_id)
    token = generate_kiosk_token(kiosk)
    url = request.build_absolute_uri(
        reverse("attendance:mark_confirm") + f"?k={kiosk.pk}&t={token}"
    )
    image = qrcode.make(url)
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    response = HttpResponse(buffer.getvalue(), content_type="image/png")
    response["Cache-Control"] = "no-store"
    return response


@login_required(login_url="accounts:login_empleado")
def mark_confirm(request):
    kiosk_id = request.GET.get("k") or request.POST.get("k")
    token = request.GET.get("t") or request.POST.get("t")
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

    if request.method == "POST":
        try:
            entry = clock_employee(employee, kiosk, token)
        except ClockError as exc:
            return render(request, "attendance/mark_error.html", {"message": str(exc)})
        return render(request, "attendance/mark_success.html", {"entry": entry})

    preview_type = next_entry_type(employee)
    return render(
        request,
        "attendance/mark_confirm.html",
        {"kiosk": kiosk, "token": token, "employee": employee, "preview_type": preview_type},
    )


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
    return render(
        request,
        "attendance/my_attendance.html",
        {
            "entries": entries,
            "summary": summary,
            "total_hours": total_hours,
            "date_from": date_from,
            "date_to": today,
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
            "chart_hours": [row["hours"] for row in rows],
        },
    )
