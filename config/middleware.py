from django.conf import settings


class DevStaticNoCacheMiddleware:
    """Fuerza a los archivos /static/ a revalidar con el servidor en cada
    carga en vez de confiar en la cache heuristica del navegador.

    Solo corre con DEBUG=True (desarrollo con runserver, sin manifest de
    hashes en el nombre del archivo): sin esto, el navegador puede seguir
    usando una copia vieja de un CSS/JS por horas despues de editarlo, y
    la pagina se ve o se comporta distinto sin ningun error visible --
    nos paso varias veces con auth-theme.css y feature-tour.js. No afecta
    produccion, donde STATIC deberia servirse con hash en el nombre.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if settings.DEBUG and request.path.startswith(settings.STATIC_URL):
            response["Cache-Control"] = "no-cache, must-revalidate"
        return response
