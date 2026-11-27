# ¿Quieres una página web?

**Tu idea, nuestra creación.** Agencia digital en Flask para mostrar modelos de sitios, probar demostraciones funcionales y recibir solicitudes por WhatsApp.

## Ejecutar localmente (Windows)
1. Instala Python 3.11 o superior.
2. Abre CMD en esta carpeta y ejecuta:
   ```bat
   py -m venv .venv
   .venv\Scripts\activate
   pip install -r requirements.txt
   ```
3. Define `SECRET_KEY` (en PowerShell: `$env:SECRET_KEY="una-clave-larga"`) y opcionalmente `WHATSAPP_NUMBER`.
4. Crea el administrador: `flask --app app:create_app create-admin` y sigue las preguntas.
5. Inicia: `flask --app app:create_app run` y abre http://127.0.0.1:5000

La primera ejecución crea tablas y carga categorías/modelos de ejemplo. No hay credenciales de administrador predefinidas.

## Publicar en Render
- Sube **todo el contenido** de este ZIP al repositorio, conservando carpetas.
- Crea un Web Service desde ese repositorio. Build Command: `pip install -r requirements.txt`; Start Command: `gunicorn wsgi:app`.
- Configura `SECRET_KEY` con un valor aleatorio largo y `WHATSAPP_NUMBER` con el número en formato internacional sin `+` ni espacios. El valor inicial está basado en el número compartido (Argentina: 549 + área + número); confirma que sea tu WhatsApp correcto.
- Recomendado: crea una base PostgreSQL en Render y copia su URL interna en `DATABASE_URL`. SQLite en el disco efímero de un servicio gratuito puede perder datos al reiniciar o desplegar.
- Para conservar archivos subidos, configura un Persistent Disk y `UPLOAD_FOLDER` dentro del punto de montaje; esta versión usa SVG/imagenes locales de muestra y no requiere subidas para funcionar.

## Funciones incluidas
- Catálogo con 12 categorías y 24 modelos de ejemplo, búsqueda y filtros.
- Cada modelo tiene una demostración HTML funcional y solicitud prearmada por WhatsApp.
- Registro, login, perfil, favoritos e historial de pedidos.
- Administración protegida: modelos, categorías, pedidos, usuarios, ajustes y estadísticas.
- Área de código para revisar archivos permitidos y guardar **borradores versionados** en base de datos. Los borradores no se ejecutan ni modifican el código desplegado desde el navegador.
- Protección CSRF, hash de contraseñas, validación, control de permisos y límites básicos de subida.

## Importante antes de vender
Los precios de ejemplo son editables y deben ajustarse. Las demostraciones son plantillas iniciales que muestran el tipo de sitio, no entregas personalizadas listas para clientes. Acordá alcance, contenido, dominio, hosting, mantenimiento y plazos antes de cobrar.
