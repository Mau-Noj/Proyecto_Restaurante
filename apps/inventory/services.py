import logging
from decimal import Decimal

from django.db import transaction

from .models import Ingredient, StockMovement

logger = logging.getLogger(__name__)

_SIGN = {
    StockMovement.MovementType.COMPRA: 1,
    StockMovement.MovementType.MERMA: -1,
    StockMovement.MovementType.CADUCIDAD: -1,
    StockMovement.MovementType.VENTA: -1,
}


@transaction.atomic
def register_movement(
    *,
    ingredient: Ingredient,
    movement_type: str,
    quantity: Decimal,
    created_by,
    reference: str = "",
) -> StockMovement:
    """Registra un movimiento y ajusta el stock.

    No bloquea el movimiento cuando el stock queda en negativo o por debajo
    del mínimo: en un restaurante la comanda ya salió a cocina, así que
    frenar el flujo por un descuadre de inventario haría más daño que el
    descuadre mismo. En su lugar se deja un log/alerta para que bodega lo
    revise (ver también `discount_recipe_for_order`, que junta esos avisos
    para mostrárselos a quien envía el pedido).
    """
    ingredient.stock = ingredient.stock + (_SIGN[movement_type] * quantity)
    ingredient.save(update_fields=["stock", "updated_at"])
    if ingredient.stock < 0:
        logger.warning(
            "Stock negativo: '%s' quedó en %s %s tras %s (%s)",
            ingredient.name,
            ingredient.stock,
            ingredient.unit,
            movement_type,
            reference,
        )
    elif ingredient.status in ("CRITICO", "BAJO"):
        logger.info(
            "Stock bajo (%s): '%s' quedó en %s %s (mínimo %s) tras %s",
            ingredient.status,
            ingredient.name,
            ingredient.stock,
            ingredient.unit,
            ingredient.min_stock,
            movement_type,
        )
    return StockMovement.objects.create(
        ingredient=ingredient,
        movement_type=movement_type,
        quantity=quantity,
        reference=reference,
        created_by=created_by,
    )


def discount_recipe_for_order(order, created_by) -> list[Ingredient]:
    """Descuenta stock de ingredientes según receta al enviar un pedido a cocina/bar.

    Devuelve los ingredientes que quedaron en negativo o en stock bajo/crítico,
    para que quien envió el pedido reciba el aviso de inmediato.
    """
    target = f"Mesa {order.table.number}" if order.table_id else "Para Llevar"
    low_stock = []
    for item in order.items.select_related("product"):
        for recipe_item in item.product.recipe_items.select_related("ingredient"):
            register_movement(
                ingredient=recipe_item.ingredient,
                movement_type=StockMovement.MovementType.VENTA,
                quantity=recipe_item.quantity * item.quantity,
                created_by=created_by,
                reference=f"Pedido #{order.pk} - {target}",
            )
            ingredient = recipe_item.ingredient
            if ingredient.stock < 0 or ingredient.status in ("CRITICO", "BAJO"):
                low_stock.append(ingredient)
    return low_stock
