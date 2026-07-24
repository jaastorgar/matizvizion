"""
Generador de tokens de recuperacion ESTABLE.

A diferencia del default_token_generator de Django, NO incluye last_login en
el hash. Por eso iniciar sesion NO invalida un link de recuperacion pendiente
(solo lo invalida cambiar la contrasena o que pasen 24h). Esto evita el
clasico "Enlace invalido" cuando el usuario se loguea entre pedir el mail y
usar el link.
"""
from django.contrib.auth.tokens import PasswordResetTokenGenerator


class StablePasswordResetTokenGenerator(PasswordResetTokenGenerator):
    def _make_hash_value(self, user, timestamp):
        # pk + hash de contrasena + email + timestamp. SIN last_login.
        return (
            str(user.pk)
            + (user.password or "")
            + str(user.email or "")
            + str(timestamp)
        )


password_reset_token = StablePasswordResetTokenGenerator()