from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer

from .notify import KIOSK_ALERT_GROUP


class KioskAlertConsumer(AsyncWebsocketConsumer):
    """Avisa en vivo a Gerente/admin cuando alguien pide entrar al kiosco
    de asistencia, para que la alerta "¿sos vos?" aparezca sin que tengan
    que refrescar la página -- lo más parecido a un push de verificación
    (2FA) que se puede hacer sin infraestructura de notificaciones nueva,
    reusando el mismo mecanismo de WebSockets que ya tiene el KDS."""

    async def connect(self):
        user = self.scope["user"]
        if not user.is_authenticated or not await self._can_receive_alerts(user):
            await self.close()
            return
        await self.channel_layer.group_add(KIOSK_ALERT_GROUP, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(KIOSK_ALERT_GROUP, self.channel_name)

    async def kiosk_alert(self, event):
        await self.send(text_data="update")

    @staticmethod
    @database_sync_to_async
    def _can_receive_alerts(user) -> bool:
        from apps.employees.models import Employee

        if user.is_staff or user.is_superuser:
            return True
        employee = getattr(user, "employee_profile", None)
        return bool(employee and employee.position == Employee.Position.GERENTE)
