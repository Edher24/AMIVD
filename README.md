# AMIVD — Sistema de Monitoreo de Afiliaciones

Sistema web desarrollado en **Flask** para la gestión, registro, control y consulta de afiliados de la Asociación de Voleibol de Tlaxcala (AVT). Incluye control de acceso por roles, digitalización de documentos, generación de reportes y exportación a Excel.

---

## 📋 Tabla de contenidos

- [Características](#-características)
- [Tecnologías](#-tecnologías)
- [Requisitos previos](#-requisitos-previos)
- [Instalación](#-instalación)
- [Configuración](#️-configuración)
- [Uso](#️-uso)
- [Estructura del proyecto](#-estructura-del-proyecto)
- [Roles y permisos](#-roles-y-permisos)
- [Tests](#-tests)
- [Autor](#-autor)

---

## ✨ Características

- 🔐 **Autenticación con roles**: Administrador, Presidente y Secretaria.
- 👥 **Registro de afiliados**: personas, entrenadores, jugadores, árbitros y directivos.
- 💳 **Registro de pagos** y seguimiento de cuotas.
- 📄 **Digitalización de documentos**: fotos, firmas e INE de afiliados.
- 📊 **Reportes del sistema** y exportación a Excel (`.xlsx`).
- ✉️ **Recuperación de contraseña** y notificaciones por correo (SMTP Gmail).
- 🛡️ **Control de acceso por rol** (RNF_06) con alertas de permisos.
- ✅ **Pruebas unitarias** con `pytest`.

---

## 🛠 Tecnologías

| Tecnología | Versión | Uso |
|------------|---------|-----|
| Python | 3.10+ | Lenguaje base |
| Flask | 3.1.3 | Framework web |
| Flask-MySQLdb | 2.0.0 | Conexión a MySQL |
| Flask-Bcrypt | 1.0.1 | Hash de contraseñas |
| Flask-Mail | 0.10.0 | Envío de correos |
| MySQL | 8.0+ | Base de datos |
| openpyxl | 3.1.5 | Exportación a Excel |
| pytest | 9.1.1 | Pruebas unitarias |
| Bootstrap | 5.x | Estilos (frontend) |

---

## 📦 Requisitos previos

- **Python 3.10 o superior** → [Descargar](https://www.python.org/downloads/)
- **MySQL Server 8.0 o superior** → [Descargar](https://dev.mysql.com/downloads/mysql/)
- **Git** → [Descargar](https://git-scm.com/downloads)
- Editor recomendado: **VS Code** → [Descargar](https://code.visualstudio.com/)

Verifica que estén instalados:

```bash
python --version
mysql --version
git --version
```

---

## 🚀 Instalación

### 1. Clona el repositorio

```bash
git clone https://github.com/Edher24/AMIVD.git
cd AMIVD
git checkout control-roles
```

### 2. Entra a la carpeta del proyecto

```bash
cd Proyecto_AVT
```

### 3. Crea y activa un entorno virtual

**Windows (PowerShell):**
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

**Windows (CMD):**
```cmd
python -m venv venv
venv\Scripts\activate.bat
```

**Linux / macOS:**
```bash
python3 -m venv venv
source venv/bin/activate
```

> Si PowerShell da error de *execution policy*, ejecuta antes:
> ```powershell
> Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
> ```

### 4. Instala las dependencias

```bash
pip install -r requirements.txt
```

### 5. Crea la base de datos e importa los datos

```bash
mysql -u root -p -e "CREATE DATABASE base_datos_amivd CHARACTER SET utf8mb4;"
mysql -u root -p base_datos_amivd < databases/base_datos_amivd_actual.sql
```

O desde **MySQL Workbench**: `Server → Data Import → Import from Self-Contained File` y selecciona `databases/base_datos_amivd_actual.sql`.

---

## ⚙️ Configuración

La configuración está en `config.py` y usa **variables de entorno** con valores por defecto para desarrollo local.

| Variable | Valor por defecto | Descripción |
|----------|-------------------|-------------|
| `MYSQL_HOST` | `localhost` | Host de MySQL |
| `MYSQL_PORT` | `3306` | Puerto de MySQL |
| `MYSQL_USER` | `root` | Usuario de MySQL |
| `MYSQL_PASSWORD` | `root` | Contraseña de MySQL |
| `MYSQL_DB` | `base_datos_amivd` | Nombre de la base de datos |
| `SECRET_KEY` | `voleibol_avt_tlaxcala_2026` | Clave secreta de Flask |

### Configuración del correo (SMTP)

```python
MAIL_SERVER = 'smtp.gmail.com'
MAIL_PORT = 587
MAIL_USE_TLS = True
MAIL_USERNAME = 'avt@gmail.com'   # ← cambiar por correo real
MAIL_PASSWORD = '1234'             # ← cambiar por App Password de Gmail
MAIL_DEFAULT_SENDER = 'avt@gmail.com'
```

> ⚠️ **Para producción:** cambia `MYSQL_PASSWORD`, `SECRET_KEY` y las credenciales de correo. En Gmail necesitas generar una **App Password** en tu cuenta (no uses tu contraseña normal).

### Ejemplo con archivo `.env` (opcional)

Si prefieres no tocar `config.py`, crea un archivo `.env` en `Proyecto_AVT/`:

```env
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=tu_contraseña
MYSQL_DB=base_datos_amivd
SECRET_KEY=tu_clave_secreta
```

Y cárgalo al inicio de `app.py` (requiere `python-dotenv`):

```python
from dotenv import load_dotenv
load_dotenv()
```

---

## ▶️ Uso

Con el entorno virtual activado y dentro de `Proyecto_AVT`:

```bash
python app.py
```

Abre tu navegador en:

```
http://127.0.0.1:5000
```

---

## 📁 Estructura del proyecto

```
ProyectoAVT/
├── Proyecto_AVT/
│   ├── app.py                  # Punto de entrada Flask
│   ├── config.py               # Configuración (BD, correo, etc.)
│   ├── requirements.txt        # Dependencias
│   ├── auth/                   # Login, logout, recuperación
│   ├── autorizar/              # Aprobación de registros
│   ├── consulta/               # Consultas y búsquedas
│   ├── paginaInicio/           # Dashboard y expedientes
│   ├── registro/               # Registro de afiliados y pagos
│   ├── reportes/               # Generación de reportes
│   ├── databases/              # Scripts SQL
│   ├── static/                 # CSS, JS, imágenes, uploads
│   ├── templates/              # Plantillas HTML (Jinja2)
│   └── test/                   # Pruebas unitarias
└── README.md
```

---

## 🔑 Roles y permisos

| Rol | Usuario | Contraseña |
|-----|---------|------------|
| Administrador | `administradorEdher` | `12345678` |
| Presidente | `presidenteEdher` | `12345678` |
| Secretaria | `secretarioEdher` | `12345678` |

El sistema aplica control de acceso por rol (**RNF_06**) con alertas visuales cuando un usuario intenta acceder a un módulo no autorizado.

---

## 🧪 Tests

Ejecutar todas las pruebas:

```bash
pytest
```

Ejecutar un módulo específico:

```bash
pytest test/test_auth.py -v
```

Módulos de prueba incluidos:

- `test_auth.py` — Login, logout, autenticación.
- `test_autorizar.py` — Aprobación de registros.
- `test_consulta.py` — Consultas y búsquedas.
- `test_paginaInicio.py` — Dashboard y expedientes.
- `test_registro.py` — Registro de afiliados y pagos.
- `test_reportes.py` — Generación de reportes.

---

## 👤 Autor

**Adriana Nicole Guzman Ahuatzi**
- GitHub: [@Edher24](https://github.com/Edher24)
- Repositorio: [AMIVD](https://github.com/Edher24/AMIVD)

---

## 📄 Licencia

Proyecto académico desarrollado para la Asociación de Voleibol de Tlaxcala (AVT).
Uso exclusivo institucional.