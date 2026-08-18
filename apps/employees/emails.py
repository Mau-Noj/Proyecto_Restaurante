from django.core.mail import send_mail


def send_welcome_email(employee, temp_password: str) -> None:
    user = employee.user
    subject = "Bienvenido a Zennin Bistro — tus credenciales de acceso"
    message = (
        f"Hola {user.first_name},\n\n"
        f"Se creó tu cuenta de personal en Zennin Bistro.\n\n"
        f"Usuario: {user.username}\n"
        f"Contraseña temporal: {temp_password}\n\n"
        f"Al iniciar sesión por primera vez se te pedirá cambiarla por una "
        f"contraseña propia.\n\n"
        f"— Zennin Bistro"
    )
    send_mail(subject, message, from_email=None, recipient_list=[user.email], fail_silently=False)
