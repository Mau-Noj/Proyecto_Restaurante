import hashlib
import secrets

from django.conf import settings
from django.db import models


def _generate_secret() -> str:
    return secrets.token_hex(32)


class Kiosk(models.Model):
    """Punto físico (tablet/PC ya existente en cocina o caja) donde se
    muestra el QR rotativo para marcar entrada/salida.

    `enabled` es un interruptor que solo un Gerente/admin puede prender
    (ver attendance:toggle_kiosk_access): sin esto en True, ni siquiera la
    cuenta especial "Kiosko" puede ver la pantalla, aunque tenga la
    contraseña correcta -- así el acceso queda bajo control activo del
    administrador, no solo de quién conoce las credenciales."""

    name = models.CharField("Nombre", max_length=100)
    secret_key = models.CharField(max_length=64, default=_generate_secret, editable=False)
    enabled = models.BooleanField("Pantalla habilitada", default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "Kiosco"
        verbose_name_plural = "Kioscos"

    def __str__(self):
        return self.name


class KioskAccessRequest(models.Model):
    """Un intento de entrar a la pantalla de asistencia mientras está
    deshabilitada (ver attendance.views.attendance_display). Se muestra
    como alerta en vivo a cualquier Gerente/admin conectado (ver
    attendance.context_processors.kiosk_access_alert): "¿sos vos?" -- si
    aprueba, habilita la pantalla (Kiosk.enabled) para que la cuenta
    Kiosko pueda entrar; si rechaza, queda registrado el rechazo."""

    class Status(models.TextChoices):
        PENDIENTE = "PENDIENTE", "Pendiente"
        APROBADA = "APROBADA", "Aprobada"
        RECHAZADA = "RECHAZADA", "Rechazada"

    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="kiosk_access_requests"
    )
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDIENTE)
    created_at = models.DateTimeField(auto_now_add=True)
    responded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="kiosk_access_responded",
    )
    responded_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Solicitud de acceso al kiosco"
        verbose_name_plural = "Solicitudes de acceso al kiosco"

    def __str__(self):
        return f"{self.requested_by} · {self.get_status_display()}"


class TimeEntry(models.Model):
    """Marcación de entrada/salida.

    Es un registro de solo-INSERT: la aplicación nunca expone una forma de
    editarlo ni borrarlo (ver `apps.attendance.services`), y además la base
    de datos lo rechaza a nivel de trigger (migración 0002). Cada fila
    encadena el hash de la anterior (`prev_hash` -> `hash`), así que alterar
    cualquier registro histórico -por el motivo que sea- rompe la cadena de
    ahí en adelante y es detectable recalculándola (ver
    `services.verify_chain`). Las correcciones se hacen con un
    TimeEntryAdjustment aparte, nunca tocando esta fila.
    """

    class EntryType(models.TextChoices):
        ENTRADA = "ENTRADA", "Entrada"
        SALIDA = "SALIDA", "Salida"

    employee = models.ForeignKey(
        "employees.Employee", on_delete=models.PROTECT, related_name="time_entries"
    )
    entry_type = models.CharField(max_length=10, choices=EntryType.choices)
    kiosk = models.ForeignKey(Kiosk, on_delete=models.PROTECT, related_name="time_entries")
    token_used = models.CharField(max_length=64, unique=True)
    # No auto_now_add: el hash se calcula ANTES de guardar a partir de este
    # valor, así que tiene que ser el timestamp exacto que se persiste, no
    # uno que Django reasigne por su cuenta al hacer INSERT (ver
    # services.clock_employee, que siempre lo pasa explícito).
    timestamp = models.DateTimeField()
    prev_hash = models.CharField(max_length=64, blank=True, default="")
    hash = models.CharField(max_length=64, editable=False)

    class Meta:
        ordering = ["timestamp"]
        verbose_name = "Marcación"
        verbose_name_plural = "Marcaciones"

    def __str__(self):
        return f"{self.employee} · {self.get_entry_type_display()} · {self.timestamp:%d/%m %H:%M}"

    @property
    def receipt(self) -> str:
        """Los primeros 12 caracteres del hash, cortos para mostrarle al
        empleado como comprobante ("folio") sin exponer la cadena completa."""
        return self.hash[:12]


class TimeEntryAdjustment(models.Model):
    """Corrección sobre una marcación. Nunca se edita `TimeEntry`: esto es un
    registro nuevo, encadenado igual que TimeEntry, siempre visible para el
    empleado dueño de la marcación original (ver attendance:my_attendance)."""

    entry = models.ForeignKey(TimeEntry, on_delete=models.PROTECT, related_name="adjustments")
    adjusted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="time_adjustments_made"
    )
    reason = models.TextField("Motivo")
    previous_timestamp = models.DateTimeField()
    new_timestamp = models.DateTimeField()
    # Mismo motivo que TimeEntry.timestamp: sin auto_now_add, para que el
    # hash calculado antes de guardar sea exactamente lo que se persiste.
    created_at = models.DateTimeField()
    prev_hash = models.CharField(max_length=64, blank=True, default="")
    hash = models.CharField(max_length=64, editable=False)

    class Meta:
        ordering = ["created_at"]
        verbose_name = "Ajuste de marcación"
        verbose_name_plural = "Ajustes de marcación"

    def __str__(self):
        return f"Ajuste #{self.pk} sobre {self.entry_id}"


def compute_hash(prev_hash: str, *parts: str) -> str:
    payload = "|".join([prev_hash, *parts])
    return hashlib.sha256(payload.encode()).hexdigest()


class Shift(models.Model):
    """Horario asignado por el administrador a un empleado para un día
    puntual. `end_time` es lo que dispara que el QR nombrado de salida
    aparezca solo en la pantalla del kiosco cuando se acerca esa hora (ver
    `services.employees_leaving_now`). No bloquea la entrada -- esa sigue
    siendo libre con el QR estático (ver Kiosk / services.clock_static_entrada)
    -- ni impide marcar salida si no existe: sin turno asignado ese día, se
    usa el QR genérico rotativo de siempre."""

    employee = models.ForeignKey(
        "employees.Employee", on_delete=models.CASCADE, related_name="shifts"
    )
    date = models.DateField("Fecha")
    start_time = models.TimeField("Hora de entrada")
    end_time = models.TimeField("Hora de salida")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="shifts_created"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["date", "start_time"]
        verbose_name = "Turno"
        verbose_name_plural = "Turnos"
        constraints = [
            models.UniqueConstraint(fields=["employee", "date"], name="unique_shift_per_day")
        ]

    def __str__(self):
        return f"{self.employee} · {self.date} {self.start_time}-{self.end_time}"


class OvertimeRequest(models.Model):
    """Horas extra sobre un turno: pedidas por el empleado o propuestas por
    el administrador. Gobierna cómo se categoriza el tiempo trabajado
    (normal vs. extra) en el reporte -- la hora real de salida sigue siendo
    siempre la de TimeEntry, esto no la reemplaza.

    A diferencia de TimeEntry, este modelo sí se actualiza in-place al
    responder/aprobar (no está encadenado ni es append-only): lo que hay que
    proteger de fraude es la hora real de salida, ya cubierta por la
    bitácora inmutable; esto es una decisión de autorización sobre esa hora,
    no el registro del hecho en sí."""

    class Origin(models.TextChoices):
        EMPLEADO = "EMPLEADO", "Solicitada por el empleado"
        ADMIN = "ADMIN", "Propuesta por administración"

    class Status(models.TextChoices):
        PENDIENTE = "PENDIENTE", "Pendiente"
        APROBADA = "APROBADA", "Aprobada"
        RECHAZADA = "RECHAZADA", "Rechazada"

    shift = models.ForeignKey(Shift, on_delete=models.CASCADE, related_name="overtime_requests")
    employee = models.ForeignKey(
        "employees.Employee", on_delete=models.CASCADE, related_name="overtime_requests"
    )
    origin = models.CharField(max_length=10, choices=Origin.choices)
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="overtime_requested"
    )
    requested_minutes = models.PositiveIntegerField("Minutos solicitados/propuestos")
    approved_minutes = models.PositiveIntegerField("Minutos aprobados", null=True, blank=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDIENTE)
    note = models.CharField("Motivo / comentario", max_length=300, blank=True)
    responded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="overtime_responded",
    )
    responded_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Solicitud de horas extra"
        verbose_name_plural = "Solicitudes de horas extra"

    def __str__(self):
        return f"{self.employee} · {self.requested_minutes} min · {self.get_status_display()}"
