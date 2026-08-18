from decimal import Decimal

from django.db import transaction

from .models import Ingredient, StockMovement

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
    ingredient.stock = ingredient.stock + (_SIGN[movement_type] * quantity)
    ingredient.save(update_fields=["stock", "updated_at"])
    return StockMovement.objects.create(
        ingredient=ingredient,
        movement_type=movement_type,
        quantity=quantity,
        reference=reference,
        created_by=created_by,
    )


def discount_recipe_for_order(order, created_by) -> None:
    """Descuenta stock de ingredientes según receta al enviar un pedido a cocina/bar."""
    target = f"Mesa {order.table.number}" if order.table_id else "Para Llevar"
    for item in order.items.select_related("product"):
        for recipe_item in item.product.recipe_items.select_related("ingredient"):
            register_movement(
                ingredient=recipe_item.ingredient,
                movement_type=StockMovement.MovementType.VENTA,
                quantity=recipe_item.quantity * item.quantity,
                created_by=created_by,
                reference=f"Pedido #{order.pk} - {target}",
            )
