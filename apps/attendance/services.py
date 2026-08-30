import hashlib
import secrets
from datetime import datetime, timedelta

from django.core.cache import cache
from django.db import IntegrityError, transaction
from django.utils import timezone

from .models import (
    Kiosk,
    KioskAccessRequest,
    OvertimeRequest,
    Shift,
    TimeEntry,
    TimeEntryAdjustment,
    compute_hash,
)

TOKEN_TTL_SECONDS = 25
_GENERIC_PREFIX = "attendance-kiosk-token"
_SCOPED_PREFIX = "attendance-scoped-token"


class ClockError(Exception):
    """Error de negocio al intentar marcar (token vencido/reusado, código
    de otra persona, etc.), para distinguir de errores de programación."""


def get_default_kiosk() -> Kiosk:
    """Ya no se le pide al administrador que cree/administre kioscos --
    hay uno solo, provisto automáticamente, para no ponerle carga extra.
    La pantalla de asistencia (views.attendance_display) siempre usa este."""
    kiosk, _ = Kiosk.objects.get_or_create(name="Principal")
    return kiosk


# --- Solicitudes de acceso al kiosco ("¿sos vos?") --------------------------


def kiosko_session_is_approved(user, session_key: str) -> bool:
    """Si YA hubo un "sí" aprobado para esta sesión puntual de navegador
    -- no para la cuenta en general -- no hace falta volver a preguntar
    en cada recarga de una pantalla que ya está abierta."""
    if not session_key:
        return False
    return KioskAccessRequest.objects.filter(
        requested_by=user, session_key=session_key, status=KioskAccessRequest.Status.APROBADA
    ).exists()


def get_kiosk_access_status(user, session_key: str) -> KioskAccessRequest:
    """La solicitud a mostrarle a la cuenta Kiosko en la pantalla de
    espera: reutiliza una pendiente si ya hay una (para no crear una
    nueva en cada recarga), o se queda mostrando el último rechazo hasta
    que la persona pida explícitamente reintentar (ver
    request_new_kiosk_access) -- así un "no" por error no la deja
    trabada sin salida, pero tampoco recrea la solicitud sola en cada
    recarga y vuelve a molestar al admin sin que nadie haya pedido nada."""
    pending = KioskAccessRequest.objects.filter(
        requested_by=user, status=KioskAccessRequest.Status.PENDIENTE
    ).first()
    if pending:
        return pending

    last = KioskAccessRequest.objects.filter(requested_by=user).order_by("-created_at").first()
    if last and last.status == KioskAccessRequest.Status.RECHAZADA:
        return last

    return request_new_kiosk_access(user, session_key)


def request_new_kiosk_access(user, session_key: str) -> KioskAccessRequest:
    """Crea una solicitud nueva sin importar lo que haya antes -- para el
    botón "Reintentar" tras un rechazo, una acción explícita de la
    persona, no algo que deba pasar solo."""
    from .notify import notify_kiosk_alert

    access_request = KioskAccessRequest.objects.create(requested_by=user, session_key=session_key)
    notify_kiosk_alert()
    return access_request


@transaction.atomic
def respond_kiosk_access_request(access_request: KioskAccessRequest, admin_user, approved: bool) -> KioskAccessRequest:
    """Aprobar NO toca el interruptor global (Kiosk.enabled) -- solo
    autoriza la sesión puntual que pidió (ver kiosko_session_is_approved).
    El interruptor global sigue existiendo aparte, para cuando el admin
    quiera dejar la pantalla sin fricción a propósito."""
    if access_request.status != KioskAccessRequest.Status.PENDIENTE:
        raise ClockError("Esta solicitud ya fue respondida.")
    access_request.status = (
        KioskAccessRequest.Status.APROBADA if approved else KioskAccessRequest.Status.RECHAZADA
    )
    access_request.responded_by = admin_user
    access_request.responded_at = timezone.now()
    access_request.save(update_fields=["status", "responded_by", "responded_at"])
    return access_request


# --- Marcación genérica (kiosco de siempre: rotativo, cualquier empleado) --


def generate_kiosk_token(kiosk: Kiosk) -> str:
    """Token de un solo uso, válido por TOKEN_TTL_SECONDS, para el QR
    rotativo genérico -- lo puede usar cualquier empleado para marcar su
    propia siguiente acción (entrada o salida, lo que le toque)."""
    token = secrets.token_urlsafe(24)
    cache.set(f"{_GENERIC_PREFIX}:{kiosk.pk}:{token}", True, timeout=TOKEN_TTL_SECONDS)
    return token


def _generic_token_is_valid(kiosk: Kiosk, token: str) -> bool:
    return cache.get(f"{_GENERIC_PREFIX}:{kiosk.pk}:{token}") is not None


def _consume_generic_token(kiosk: Kiosk, token: str) -> None:
    cache.delete(f"{_GENERIC_PREFIX}:{kiosk.pk}:{token}")


# --- QR estático de entrada (siempre igual, sin expirar, para todos) -------
#
# Riesgo aceptado a propósito: como nunca cambia, alguien podría fotografiarlo
# una vez y compartirlo para marcar entrada sin estar físicamente presente.
# Se acepta porque el costado sensible (cuánto tiempo se pagó) depende de la
# SALIDA, que sigue exigiendo el QR rotativo con dueño (ver más abajo). Este
# QR además solo puede generar ENTRADA, nunca SALIDA (ver clock_static_entrada).


def static_entrada_token(kiosk: Kiosk) -> str:
    """Determinístico a partir del secret_key del kiosco: mismo kiosco,
    mismo token, siempre -- por diseño, no es de un solo uso ni expira."""
    return hashlib.sha256(f"entrada-estatica:{kiosk.secret_key}".encode()).hexdigest()[:32]


# --- QR con dueño (salida programada de un empleado puntual) ---------------


def generate_scoped_token(kiosk: Kiosk, employee) -> str:
    """Token de un solo uso atado a UN empleado específico -- si otra
    persona lo escanea, se rechaza (ver clock_scoped)."""
    token = secrets.token_urlsafe(24)
    cache.set(f"{_SCOPED_PREFIX}:{kiosk.pk}:{employee.pk}:{token}", True, timeout=TOKEN_TTL_SECONDS)
    return token


def _scoped_token_is_valid(kiosk: Kiosk, employee, token: str) -> bool:
    return cache.get(f"{_SCOPED_PREFIX}:{kiosk.pk}:{employee.pk}:{token}") is not None


def _consume_scoped_token(kiosk: Kiosk, employee, token: str) -> None:
    cache.delete(f"{_SCOPED_PREFIX}:{kiosk.pk}:{employee.pk}:{token}")


def next_entry_type(employee) -> str:
    """ENTRADA/SALIDA se alternan solos según la última marcación del
    empleado -- no se le pregunta, para que no pueda "elegir mal" a
    propósito ni por error."""
    last = TimeEntry.objects.filter(employee=employee).order_by("-timestamp").first()
    if last is None or last.entry_type == TimeEntry.EntryType.SALIDA:
        return TimeEntry.EntryType.ENTRADA
    return TimeEntry.EntryType.SALIDA


def _insert_time_entry(employee, kiosk: Kiosk, entry_type: str, token: str) -> TimeEntry:
    """Núcleo compartido de inserción + encadenado de hash. `token` solo
    necesita ser único para la fila (auditoría); su validación (si expira,
    si es de un solo uso, si tiene dueño) ya se resolvió antes de llamar
    esto -- ver clock_employee / clock_static_entrada / clock_scoped."""
    last_entry = TimeEntry.objects.select_for_update().order_by("-id").first()
    prev_hash = last_entry.hash if last_entry else ""
    timestamp = timezone.now()
    new_hash = compute_hash(prev_hash, str(employee.pk), entry_type, timestamp.isoformat(), token)
    entry = TimeEntry(
        employee=employee,
        entry_type=entry_type,
        kiosk=kiosk,
        token_used=token,
        timestamp=timestamp,
        prev_hash=prev_hash,
        hash=new_hash,
    )
    try:
        entry.save()
    except IntegrityError as exc:
        raise ClockError("Este código ya se usó. Escanea el QR de nuevo.") from exc
    return entry


@transaction.atomic
def clock_employee(employee, kiosk: Kiosk, token: str) -> TimeEntry:
    """QR genérico rotativo: cualquier empleado marca su propia siguiente
    acción (entrada si no tenía nada pendiente, salida si ya había
    entrado). Es el respaldo para cuando no hay turno asignado."""
    if not _generic_token_is_valid(kiosk, token):
        raise ClockError("Este código ya expiró. Escanea el QR de nuevo.")
    entry_type = next_entry_type(employee)
    entry = _insert_time_entry(employee, kiosk, entry_type, token)
    _consume_generic_token(kiosk, token)
    return entry


@transaction.atomic
def clock_static_entrada(employee, kiosk: Kiosk, token: str) -> TimeEntry:
    """QR estático de entrada: solo puede producir ENTRADA. Si el empleado
    ya tiene una entrada sin salida, se rechaza -- este QR no sirve para
    marcar salida bajo ningún caso."""
    if token != static_entrada_token(kiosk):
        raise ClockError("Código de entrada inválido para este kiosco.")
    if next_entry_type(employee) != TimeEntry.EntryType.ENTRADA:
        raise ClockError(
            "Ya tenés una entrada registrada sin salida. Este código es solo para entrada."
        )
    # Token sintético único por marcación (auditoría), aunque el QR en
    # pantalla sea siempre el mismo.
    unique_token = f"{token}:{secrets.token_urlsafe(12)}"
    return _insert_time_entry(employee, kiosk, TimeEntry.EntryType.ENTRADA, unique_token)


@transaction.atomic
def clock_scoped(scanning_employee, kiosk: Kiosk, token: str, owner_employee) -> TimeEntry:
    """QR con dueño (salida programada): solo `owner_employee` puede
    usarlo. Si otro empleado lo escanea (aunque esté autenticado con su
    propia cuenta), se rechaza explícitamente."""
    if scanning_employee.pk != owner_employee.pk:
        raise ClockError(
            f"Este código es para {owner_employee.user.get_full_name() or owner_employee.user.username}."
        )
    if not _scoped_token_is_valid(kiosk, owner_employee, token):
        raise ClockError("Este código ya expiró. Escanea el QR de nuevo.")
    entry_type = next_entry_type(owner_employee)
    entry = _insert_time_entry(owner_employee, kiosk, entry_type, token)
    _consume_scoped_token(kiosk, owner_employee, token)
    return entry


# --- Turnos y horas extra ---------------------------------------------------


def effective_shift_end(shift: Shift) -> datetime:
    """Hora de salida programada, extendida por cualquier hora extra ya
    aprobada sobre ese turno."""
    naive_end = datetime.combine(shift.date, shift.end_time)
    end_dt = timezone.make_aware(naive_end, timezone.get_current_timezone())
    approved_minutes = sum(
        req.approved_minutes or 0
        for req in shift.overtime_requests.filter(status=OvertimeRequest.Status.APROBADA)
    )
    return end_dt + timedelta(minutes=approved_minutes)


def employees_leaving_now(window_minutes: int = 15) -> list[dict]:
    """Empleados con turno asignado hoy, todavía "adentro" (su última
    marcación fue ENTRADA), cuya hora de salida efectiva (con horas extra
    aprobadas ya sumadas) está a `window_minutes` o menos, o ya pasó. Es
    lo que decide a quién mostrarle su QR nombrado en el kiosco."""
    today = timezone.localdate()
    now = timezone.now()
    results = []
    shifts = Shift.objects.filter(date=today).select_related("employee__user").prefetch_related(
        "overtime_requests"
    )
    for shift in shifts:
        if next_entry_type(shift.employee) != TimeEntry.EntryType.SALIDA:
            continue  # no está "adentro" (no marcó entrada, o ya marcó salida)
        end = effective_shift_end(shift)
        if now >= end - timedelta(minutes=window_minutes):
            results.append({"employee": shift.employee, "shift": shift, "effective_end": end})
    results.sort(key=lambda row: row["effective_end"])
    return results


@transaction.atomic
def request_overtime(shift: Shift, requested_by, origin: str, minutes: int, note: str = "") -> OvertimeRequest:
    return OvertimeRequest.objects.create(
        shift=shift,
        employee=shift.employee,
        origin=origin,
        requested_by=requested_by,
        requested_minutes=minutes,
        note=note,
    )


@transaction.atomic
def respond_overtime_proposal(request: OvertimeRequest, employee_user, accepted_minutes: int) -> OvertimeRequest:
    """El empleado responde a una propuesta del administrador: acepta el
    total o una cantidad menor (una contraoferta mayor no tiene sentido acá,
    se limita al máximo propuesto). Queda aprobada de inmediato -- como
    nunca puede superar lo que administración ya autorizó, no hay riesgo en
    aprobarla sin otra vuelta de confirmación."""
    if request.status != OvertimeRequest.Status.PENDIENTE:
        raise ClockError("Esta propuesta ya fue respondida.")
    accepted_minutes = max(0, min(accepted_minutes, request.requested_minutes))
    request.approved_minutes = accepted_minutes
    request.status = (
        OvertimeRequest.Status.APROBADA if accepted_minutes > 0 else OvertimeRequest.Status.RECHAZADA
    )
    request.responded_by = employee_user
    request.responded_at = timezone.now()
    request.save(update_fields=["approved_minutes", "status", "responded_by", "responded_at"])
    return request


@transaction.atomic
def decide_overtime_request(request: OvertimeRequest, admin_user, approved: bool, approved_minutes=None) -> OvertimeRequest:
    """Un Gerente aprueba o rechaza una solicitud iniciada por el
    empleado."""
    if request.status != OvertimeRequest.Status.PENDIENTE:
        raise ClockError("Esta solicitud ya fue respondida.")
    request.status = OvertimeRequest.Status.APROBADA if approved else OvertimeRequest.Status.RECHAZADA
    request.approved_minutes = (
        (approved_minutes if approved_minutes is not None else request.requested_minutes)
        if approved
        else 0
    )
    request.responded_by = admin_user
    request.responded_at = timezone.now()
    request.save(update_fields=["status", "approved_minutes", "responded_by", "responded_at"])
    return request


@transaction.atomic
def create_adjustment(entry: TimeEntry, admin_user, reason: str, new_timestamp) -> TimeEntryAdjustment:
    last = TimeEntryAdjustment.objects.select_for_update().order_by("-id").first()
    prev_hash = last.hash if last else ""
    created_at = timezone.now()
    new_hash = compute_hash(
        prev_hash,
        str(entry.pk),
        str(admin_user.pk),
        new_timestamp.isoformat(),
        created_at.isoformat(),
    )
    return TimeEntryAdjustment.objects.create(
        entry=entry,
        adjusted_by=admin_user,
        reason=reason,
        previous_timestamp=entry.timestamp,
        new_timestamp=new_timestamp,
        created_at=created_at,
        prev_hash=prev_hash,
        hash=new_hash,
    )


# --- Reportes ----------------------------------------------------------------


def effective_timestamp(entry: TimeEntry):
    """La hora "real" de una marcación: la del último ajuste si lo hay, si
    no la original. Nunca se sobreescribe `entry.timestamp` -- esto solo se
    usa para calcular reportes, la fila original queda intacta siempre."""
    last_adjustment = entry.adjustments.order_by("-created_at").first()
    return last_adjustment.new_timestamp if last_adjustment else entry.timestamp


def _split_session(session_start, session_end, shift: Shift | None) -> dict:
    """Reparte una sesión ENTRADA->SALIDA en horas normales / extra
    aprobadas / extra SIN autorizar (se quedó más de lo aprobado) / sin
    turno asignado ese día."""
    zero = {"regular": 0.0, "overtime": 0.0, "unauthorized": 0.0, "no_shift": 0.0}
    if session_end <= session_start:
        return zero

    if shift is None:
        hours = (session_end - session_start).total_seconds() / 3600
        return {**zero, "no_shift": hours}

    naive_end = datetime.combine(shift.date, shift.end_time)
    shift_end = timezone.make_aware(naive_end, timezone.get_current_timezone())
    overtime_end = effective_shift_end(shift)

    def _hours(a, b):
        return max((b - a).total_seconds() / 3600, 0.0)

    regular_end = min(session_end, shift_end)
    regular = _hours(session_start, regular_end)

    overtime_window_end = min(session_end, overtime_end)
    overtime = _hours(max(session_start, shift_end), overtime_window_end)

    unauthorized = _hours(max(session_start, overtime_end), session_end)

    return {**zero, "regular": regular, "overtime": overtime, "unauthorized": unauthorized}


def worked_summary(employee, date_from, date_to) -> list[dict]:
    """Empareja ENTRADA->SALIDA consecutivas (con ajustes ya aplicados),
    las agrupa por día calendario y separa horas normales / extra
    aprobadas / extra sin autorizar / sin turno asignado, según el Shift
    del día (si existe)."""
    entries = list(
        TimeEntry.objects.filter(
            employee=employee, timestamp__date__gte=date_from, timestamp__date__lte=date_to
        )
        .prefetch_related("adjustments")
        .order_by("timestamp")
    )
    shifts_by_date = {
        shift.date: shift
        for shift in Shift.objects.filter(
            employee=employee, date__gte=date_from, date__lte=date_to
        ).prefetch_related("overtime_requests")
    }

    by_day: dict = {}
    pending_start = None
    for entry in entries:
        effective = effective_timestamp(entry)
        if entry.entry_type == TimeEntry.EntryType.ENTRADA:
            pending_start = effective
        elif entry.entry_type == TimeEntry.EntryType.SALIDA and pending_start is not None:
            local_start = timezone.localtime(pending_start)
            local_end = timezone.localtime(effective)
            day = local_start.date()
            shift = shifts_by_date.get(day)
            split = _split_session(local_start, local_end, shift)

            row = by_day.setdefault(
                day,
                {"date": day, "regular": 0.0, "overtime": 0.0, "unauthorized": 0.0, "no_shift": 0.0, "sessions": 0},
            )
            for key in ("regular", "overtime", "unauthorized", "no_shift"):
                row[key] += split[key]
            row["sessions"] += 1
            pending_start = None

    rows = sorted(by_day.values(), key=lambda row: row["date"])
    for row in rows:
        for key in ("regular", "overtime", "unauthorized", "no_shift"):
            row[key] = round(row[key], 2)
        row["hours"] = round(row["regular"] + row["overtime"] + row["unauthorized"] + row["no_shift"], 2)
    return rows


def verify_chain() -> bool:
    """Recalcula toda la cadena de TimeEntry y confirma que cada hash
    coincide con lo que se esperaría a partir del anterior -- si alguna fila
    fue alterada por fuera de la aplicación (o el trigger de la base de
    datos falló/se removió), esto lo detecta. Pensado para correrse manual
    u ocasionalmente (management command / shell), no en el hot path."""
    prev_hash = ""
    for entry in TimeEntry.objects.order_by("id"):
        expected = compute_hash(
            prev_hash,
            str(entry.employee_id),
            entry.entry_type,
            entry.timestamp.isoformat(),
            entry.token_used,
        )
        if entry.hash != expected or entry.prev_hash != prev_hash:
            return False
        prev_hash = entry.hash
    return True
