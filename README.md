# Matizvisión — Plataforma E-Commerce y Agendamiento Clínico

Sistema web integral para Óptica Matiz Visión desarrollado con **Django**, **Django REST Framework (DRF)** y frontend interactivo modular.

---

## 🏗️ Arquitectura y Estructura del Proyecto

El proyecto está organizado en módulos desacoplados:

* **`accounts/`**: Autenticación JWT (`SimpleJWT`), modelo de usuario personalizado (`CustomUser`) con roles (Cliente, Vendedor, Admin), perfiles específicos (`PerfilCliente`, `PerfilVendedor`), flujos de compras como invitado y recuperación segura de contraseñas.
* **`store/`**: Catálogo comercial, categorías, productos, variantes/colores, control de inventario y modelo de graduación óptica numérica (`store.RecetaOptica`).
* **`orders/`**: Carrito de compras, ciclo de vida de órdenes de compra (estados, códigos únicos no secuenciales `MV-YYYY-XXXXX`), seguimiento público, solicitudes de devolución y aplicación de garantías SERNAC.
* **`recetas/`**: Gestión de documentos clínicos y recetas médicas digitalizadas (`recetas.Receta` en PDF/JPG/PNG con rutas ofuscadas por UUID).
* **`payments/`**: Integración con pasarela de pagos Transbank Webpay Plus (commit atómico, idempotencia y registro de auditoría en `LogPago`).
* **`appointments/`**: Agendamiento clínico de citas médicas con tecnólogos médicos, gestión de bloques horarios y validación de consentimientos de salud visual.
* **`core/`**: Parámetros globales (sucursales), APIs de administración (`/api/admin/`), métricas de negocio (KPIs), centro de notificaciones por correo y comandos de mantenimiento.
* **`web/`**: Vistas de presentación y enrutamiento de plantillas HTML para la navegación web.

---

## 👓 Nota sobre los Modelos de Recetas

Para evitar confusiones en el desarrollo:
1. **`store.models.RecetaOptica`**: Registra los valores numéricos y dioptrías (esfera OD/OI, cilindro, eje, adición) asociados al perfil del cliente para configurar cristales graduados.
2. **`recetas.models.Receta`**: Gestiona los documentos adjuntos (archivos PDF o imágenes escaneadas) cargados por el cliente o el staff para respaldar sus compras y tratamientos.

---

## 🚀 Puesta en Marcha (Desarrollo)

1. **Activar entorno virtual:**
   ```bash
   # Windows PowerShell
   .\env\Scripts\Activate.ps1
   ```

2. **Instalar dependencias:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configurar variables de entorno:**
   Crear o revisar el archivo `.env` en la raíz de `matizvizion/` con las credenciales de base de datos PostgreSQL y llaves de prueba.

4. **Aplicar migraciones:**
   ```bash
   python manage.py migrate
   ```

5. **Cargar datos de prueba (opcional):**
   ```bash
   python manage.py seed_garantias
   python manage.py seed_demo
   ```

6. **Iniciar servidor:**
   ```bash
   python manage.py runserver
   ```