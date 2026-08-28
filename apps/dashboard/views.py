from django.shortcuts import render

from apps.accounts.decorators import staff_required

# Esqueleto: todos los modulos apuntan a "proximamente" hasta que se
# construyan de verdad. El icono es un nombre de Material Symbols.
# "url_name" solo se agrega cuando el modulo ya tiene una vista real.
MODULES = [
    {"code": "REG", "name": "Personal", "icon": "badge", "url_name": "employees:list"},
    {"code": "MESA", "name": "Mesas y Salón", "icon": "table_restaurant"},
    {"code": "ORD", "name": "Órdenes", "icon": "receipt_long"},
    {
        "code": "COC",
        "name": "Cocina (KDS)",
        "icon": "soup_kitchen",
        "url_name": "kds:report_prep_times",
    },
    {"code": "PAG", "name": "Pagos", "icon": "point_of_sale", "url_name": "payments:index"},
    {
        "code": "CAT",
        "name": "Catálogo y Menú",
        "icon": "restaurant_menu",
        "url_name": "catalog:index",
    },
    {"code": "INV", "name": "Inventario", "icon": "inventory_2", "url_name": "inventory:index"},
    {"code": "PUR", "name": "Compras", "icon": "shopping_cart"},
    {"code": "RES", "name": "Reservaciones", "icon": "event_seat"},
    {"code": "DEL", "name": "Delivery", "icon": "moped"},
    {"code": "RRHH", "name": "Turnos y Propinas", "icon": "schedule"},
    {"code": "BI", "name": "Reportes", "icon": "monitoring"},
    {"code": "QR", "name": "Menú QR", "icon": "qr_code_2"},
    {"code": "CRM", "name": "Fidelización", "icon": "loyalty"},
    {"code": "CFG", "name": "Configuración", "icon": "settings"},
]


@staff_required
def index(request):
    return render(request, "dashboard/index.html", {"modules": MODULES})
