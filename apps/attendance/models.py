import hashlib
import secrets

from django.conf import settings
from django.db import models


def _generate_secret() -> str:
    return secrets.token_hex(32)


class Kiosk(models.Model):
    """Punto físico (tablet/PC ya existente en cocina o caja) donde se
    muestra el QR rotativo para marcar entrada/salida."""

    name = models.CharField("Nombre", max_length=100)
    secret_key = models.CharField(max_length=64, default=_generate_secret, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "Kiosco"
        verbose_name_plural = "Kioscos"

    def __str__(self):
        return self.name


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
    timestamp = models.DateTimeField(auto_now_add=True)
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
    created_at = models.DateTimeField(auto_now_add=True)
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
