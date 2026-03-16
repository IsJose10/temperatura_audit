# RANSA - Auditoría de Temperaturas

Esta es una aplicación web responsiva diseñada para facilitar y digitalizar el proceso de auditoría de temperaturas en cámaras de refrigeración y congelación. Permite a los auditores registrar productos, observaciones, temperaturas y evidencias fotográficas desde cualquier dispositivo (con enfoque Mobile-First).

## Arquitectura del Proyecto

El proyecto está construido con un stack moderno y ligero de Python:

*   **Backend Framework:** FastAPI (rápido, tipado estático, documentación automática).
*   **Base de Datos:** MySQL (gestionado a través de SQLAlchemy ORM).
*   **Frontend HTML:** Plantillas Jinja2 puras junto a HTML5, CSS3 y JavaScript moderno (Vanilla). No requiere compilar frontend.
*   **Seguridad:** Autenticación basada en JWT (JSON Web Tokens) y contraseñas hasheadas (Passlib/Bcrypt).

### Estructura de Carpetas

```
temperatura_audit/
├── main.py                  # Punto de entrada de la aplicación y montaje de rutas HTML
├── database.py              # Configuración de conexión a la base de datos MySQL
├── config.py                # Variables de entorno y configuración general
├── requirements.txt         # Dependencias de Python (pip install -r requirements.txt)
│
├── models/                  # Declaraciones de clases Base de SQLAlchemy (Tablas BD)
│   ├── auditoria.py         # Tablas de Auditorias y AuditoriaDetalle
│   ├── camara.py            # Tabla de Cámaras (Refrigeradores)
│   ├── sede.py              # Tabla de Sedes (Ej: Galapa, Medellín)
│   └── usuario.py           # Tabla de Usuarios (Administradores y Auditores)
│
├── schemas/                 # Modelos de Pydantic para validación de datos API/JSON
│   ├── auditoria.py
│   ├── camara.py
│   └── usuario.py
│
├── routes/                  # Controladores / Endpoints del API REST
│   ├── auth.py              # Lógica de Login y Tokens
│   ├── auditoria.py         # Creación de auditorías, guardado de fotos y registros
│   ├── dashboard.py         # Cálculos estadísticos (promedios, métricas, etc.)
│   ├── historico.py         # Búsqueda y visualización de auditorías pasadas
│   └── usuarios.py          # Gestión de usuarios (CRUD) por parte de administradores
│
├── templates/               # Archivos HTML (Renderizados por Jinja2)
│   ├── base.html            # Plantilla padre con imports comunes de CSS/JS
│   ├── login.html           # Pantalla de inicio de sesión
│   ├── dashboard.html       # Panel de indicadores generales (Gráficos)
│   ├── auditoria.html       # Pantalla principal para toma de auditorías de cámara
│   ├── historico.html       # Listado de auditorías realizadas
│   ├── detalle_auditoria.html # Vista completa del detalle de una auditoría + fotos
│   └── admin_usuarios.html  # Panel de creación/edición de usuarios (Solo Admin)
│
└── static/                  # Archivos estáticos de la app
    ├── css/                 # Hojas de estilo y variables (theme)
    ├── img/                 # Logotipos y assets visuales genéricos
    ├── js/                  # Scripts base reutilizables
    └── uploads/             # Carpeta generada donde se guardan las fotos de las auditorias
```

## Guía de Uso Rápido

### Perfiles de Usuario
La aplicación maneja **Roles** (`administrador` y `auditor`). 
*   **Auditor:** Solo tiene acceso a la toma de inventario, su historial personal y su perfil regional.
*   **Administrador:** Puede acceder al Dashboard global, a las auditorías de todas las regiones y gestionar (crear/deshabilitar) usuarios en el panel de administrador.

### Flujo de Trabajo (Auditoría)
1. El auditor Inicia sesión.
2. Ingresa a la pestaña **📋 Auditoría**.
3. Selecciona la **Sede** en la que se encuentra físicamente (Ej: Galapa).
4. El sistema crea la cabecera de la auditoría y lista las cámaras de esa sede.
5. El auditor selecciona la **Cámara** a evaluar (Ej: Precava Congelado).
6. Digita el producto, toma la temperatura, escribe observaciones y opcionalmente **captura una Foto de Evidencia** abriendo la cámara en el mismo equipo.
7. Hace clic en *Guardar*. El sistema indicará el progreso. 
8. Esa cámara se bloqueará en el menú indicando **(Completada)** para evitar sobreescribirla por error.
9. Repetir hasta completar todas las cámaras.

### Flujo de Trabajo (Análisis y Revisión)
1. Un Gerente/Admin inicia sesión y entra al **📊 Dashboard**.
2. Observa recuadros numéricos con auditorías en progreso/completadas.
3. Revisa gráficos de **promedios de temperatura por mes** o **por sedes**.
4. Revisa la tabla de **Rango de Temperaturas**, que enlista las temperaturas mínimas y máximas históricas alcanzadas por cada cámara. 
5. Si requiere escarbar, va a la pestaña **📚 Histórico**, filtra por sede o estado.
6. Al hacer clic en un registro del histórico, la aplicación lo redirige al **Detalle Completo**, mostrando exactamente a qué hora el auditor tomó el registro, los grados e incluye la visualización grande de la foto tomada.

---

## Despliegue Técnico y Operación

### Pre-requisitos
*   Python 3.10 o superior
*   Base de datos MySQL (por ejemplo mediante XAMPP u otro servidor)

### Pasos
1. Clonar el repositorio.
2. Crear un entorno virtual: `python -m venv venv` y activarlo.
3. Instalar librerías: `pip install -r requirements.txt`.
4. Configurar el archivo `.env` o las variables en `config.py` para apuntar a la base de datos correcta.
5. Iniciar la base de datos local de MySQL.
6. Ejecutar el servidor con Uvicorn: `uvicorn main:app --reload`.

*Nota:* Al hacer su primera ejecución, el archivo `main.py` contiene una función auto-ejecutable `seed_data()` que crea automáticamente las tablas de la base de datos (y la base de datos misma) e inserta a un usuario administrador por defecto (`admin` / `admin123`) e inyecta la lista inicial de cámaras/sedes permitiendo iniciar pruebas de inmediato.
