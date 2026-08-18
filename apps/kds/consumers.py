from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer


class KdsConsumer(AsyncWebsocketConsumer):
    """Avisa a la pantalla de Cocina o Bar cuando hay pedidos nuevos o
    entregados, para actualizarla sin tener que refrescar a ciegas."""

    async def connect(self):
        self.station = self.scope["url_route"]["kwargs"]["station"]
        user = self.scope["user"]
        if not user.is_authenticated or not await self._user_can_access(user, self.station):
            await self.close()
            return
        self.group_name = f"kds_{self.station}"
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, "group_name"):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def kds_update(self, event):
        await self.send(text_data="update")

    @staticmethod
    @database_sync_to_async
    def _user_can_access(user, station: str) -> bool:
        from apps.employees.models import Employee

        employee = getattr(user, "employee_profile", None)
        if not employee:
            return False
        if station == "cocina":
            return employee.position == Employee.Position.COCINERO
        return employee.position == Employee.Position.BARTENDER
