import os

from django import template
from django.contrib.staticfiles import finders
from django.templatetags.static import static

register = template.Library()


@register.simple_tag
def static_v(path):
    """Igual que {% static %}, pero agrega ?v=<mtime del archivo> al final.

    Daphne sirve /static/ con un handler ASGI que se salta el middleware
    y las cabeceras de cache de Django por completo (ASGIStaticFilesHandler
    intercepta la peticion antes de que llegue a la app), asi que ponerle
    Cache-Control a la respuesta no sirve de nada aqui. Cambiar la URL en
    vez de eso funciona siempre, sin importar quien sirva el archivo: el
    navegador trata "?v=123" y "?v=456" como URLs distintas, asi que no
    hay copia vieja que revalidar -- se pide una nueva de una vez.
    """
    url = static(path)
    absolute_path = finders.find(path)
    if not absolute_path:
        return url
    version = int(os.path.getmtime(absolute_path))
    separator = "&" if "?" in url else "?"
    return f"{url}{separator}v={version}"
