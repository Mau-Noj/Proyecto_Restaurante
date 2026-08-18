from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer


def notify_station(station: str) -> None:
    channel_layer = get_channel_layer()
    if channel_layer is None:
        return
    async_to_sync(channel_layer.group_send)(f"kds_{station}", {"type": "kds_update"})


def notify_order_stations(order) -> None:
    """Avisa a Cocina y/o Bar según las categorías de los productos del pedido."""
    stations = {
        item.product.category.station
        for item in order.items.select_related("product__category")
    }
    for station in stations:
        notify_station(station.lower())
