from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

KIOSK_ALERT_GROUP = "kiosk_alerts"


def notify_kiosk_alert() -> None:
    """Avisa en vivo (WebSocket) a cualquier Gerente/admin conectado que
    hay una solicitud de acceso al kiosco esperando respuesta -- sin esto,
    solo se enterarían al refrescar/navegar a otra página (ver
    apps.attendance.consumers.KioskAlertConsumer)."""
    channel_layer = get_channel_layer()
    if channel_layer is None:
        return
    async_to_sync(channel_layer.group_send)(KIOSK_ALERT_GROUP, {"type": "kiosk_alert"})
