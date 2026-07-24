"""
Backend de correo para DESARROLLO que imprime el cuerpo en TEXTO PLANO legible.

A diferencia del console.EmailBackend de Django (que serializa el mensaje MIME
en quoted-printable, convirtiendo '=' en '=3D' y cortando lineas largas con '=',
lo que corrompe los links al copiarlos a mano), este backend escribe message.body
tal cual. Asi el link de recuperacion sale limpio y copiable en la terminal.
En PRODUCCION se usa SMTP real (EMAIL_BACKEND en .env), este backend no se toca.
"""
import sys

from django.core.mail.backends.base import BaseEmailBackend


class PlainConsoleBackend(BaseEmailBackend):
    def send_messages(self, email_messages):
        if not email_messages:
            return 0
        count = 0
        for message in email_messages:
            try:
                sys.stdout.write('\n' + ('-' * 72) + '\n')
                sys.stdout.write('MAIL (texto plano) Para: %s\n' % ', '.join(message.to))
                sys.stdout.write('Asunto: %s\n' % message.subject)
                sys.stdout.write('-' * 72 + '\n')
                sys.stdout.write(message.body)
                if not message.body.endswith('\n'):
                    sys.stdout.write('\n')
                sys.stdout.write('-' * 72 + '\n')
                sys.stdout.flush()
                count += 1
            except Exception:
                if not self.fail_silently:
                    raise
        return count