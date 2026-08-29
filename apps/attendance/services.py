import secrets

from django.core.cache import cache
from django.db import IntegrityError, transaction
from django.utils import timezone

from .models import Kiosk, TimeEntry, TimeEntryAdjustment, compute_hash

TOKEN_TTL_SECONDS = 25
_CACHE_PREFIX = "attendance-kiosk-token"


class ClockError(Exception):
    """Error de negocio al intentar marcar (token vencido/reusado, etc.),
    para distinguir de errores de programación en las vistas."""


def generate_kiosk_token(kiosk: Kiosk) -> str:
    """Genera un token de un solo uso, válido por TOKEN_TTL_SECONDS, para el
    QR que se muestra en el kiosco. El secret_key del kiosco entra en el
    token para que un QR fotografiado de OTRO kiosco no sirva aquí."""
    token = secrets.token_urlsafe(24)
    cache.set(f"{_CACHE_PREFIX}:{kiosk.pk}:{token}", True, timeout=TOKEN_TTL_SECONDS)
    return token


def _token_is_valid(kiosk: Kiosk, token: str) -> bool:
    return cache.get(f"{_CACHE_PREFIX}:{kiosk.pk}:{token}") is not None


def next_entry_type(employee) -> str:
    """ENTRADA/SALIDA se alternan solos según la última marcación del
    empleado -- no se le pregunta, para que no pueda "elegir mal" a
    propósito ni por error."""
    last = TimeEntry.objects.filter(employee=employee).order_by("-timestamp").first()
    if last is None or last.entry_type == TimeEntry.EntryType.SALIDA:
        return TimeEntry.EntryType.ENTRADA
    return TimeEntry.EntryType.SALIDA


@transaction.atomic
def clock_employee(employee, kiosk: Kiosk, token: str) -> TimeEntry:
    if not _token_is_valid(kiosk, token):
        raise ClockError("Este código ya expiró. Escanea el QR de nuevo.")

    entry_type = next_entry_type(employee)
    last_entry = (
        TimeEntry.objects.select_for_update().order_by("-id").first()
    )
    prev_hash = last_entry.hash if last_entry else ""
    timestamp = timezone.now()
    new_hash = compute_hash(
        prev_hash, str(employee.pk), entry_type, timestamp.isoformat(), token
    )
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

    # Un solo uso: aunque el TTL del cache todavia no haya vencido, se
    # invalida de inmediato para que no se pueda reintentar dos veces
    # con la misma foto del QR dentro de la ventana de 25s.
    cache.delete(f"{_CACHE_PREFIX}:{kiosk.pk}:{token}")
    return entry


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


def effective_timestamp(entry: TimeEntry):
    """La hora "real" de una marcación: la del último ajuste si lo hay, si
    no la original. Nunca se sobreescribe `entry.timestamp` -- esto solo se
    usa para calcular reportes, la fila original queda intacta siempre."""
    last_adjustment = entry.adjustments.order_by("-created_at").first()
    return last_adjustment.new_timestamp if last_adjustment else entry.timestamp


def worked_summary(employee, date_from, date_to) -> list[dict]:
    """Empareja ENTRADA->SALIDA consecutivas (usando la hora efectiva, ya
    con ajustes aplicados) y las agrupa por día calendario según la
    ENTRADA, para sacar días trabajados y horas por día."""
    entries = list(
        TimeEntry.objects.filter(
            employee=employee, timestamp__date__gte=date_from, timestamp__date__lte=date_to
        )
        .prefetch_related("adjustments")
        .order_by("timestamp")
    )

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
            hours = (local_end - local_start).total_seconds() / 3600
            row = by_day.setdefault(day, {"date": day, "hours": 0.0, "sessions": 0})
            row["hours"] += max(hours, 0.0)
            row["sessions"] += 1
            pending_start = None

    rows = sorted(by_day.values(), key=lambda row: row["date"])
    for row in rows:
        row["hours"] = round(row["hours"], 2)
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
