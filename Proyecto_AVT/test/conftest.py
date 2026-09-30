# test/conftest.py
import pytest
from unittest.mock import MagicMock
from pathlib import Path
import sys

# ══════════════════════════════════════════════════
# CONFIGURACIÓN DE RUTAS (PORTABLE)
# ══════════════════════════════════════════════════

# Ruta del archivo actual: test/conftest.py
ARCHIVO_ACTUAL = Path(__file__).resolve()

# Subir dos niveles: test/ → Proyecto_AVT/
RAIZ_PROYECTO = ARCHIVO_ACTUAL.parent.parent

# Carpetas del proyecto
CARPETA_TEMPLATES = RAIZ_PROYECTO / 'templates'
CARPETA_STATIC = RAIZ_PROYECTO / 'static'

# Asegurar que la raíz esté en el path de Python
sys.path.insert(0, str(RAIZ_PROYECTO))


# ══════════════════════════════════════════════════
# UTILIDAD: Mockear solo si el atributo existe
# ══════════════════════════════════════════════════

def _mock_si_existe(mocker, path, mock):
    """Intenta mockear path; si el atributo no existe, no falla."""
    try:
        mocker.patch(path, mock)
    except AttributeError:
        pass


# ══════════════════════════════════════════════════
# FIXTURE: App Flask
# ══════════════════════════════════════════════════

@pytest.fixture
def app_flask():
    """Crea una app Flask con TODOS los blueprints y las plantillas reales."""
    from flask import Flask
    from config import Config
    
    app = Flask(
        __name__,
        template_folder=str(CARPETA_TEMPLATES),
        static_folder=str(CARPETA_STATIC)
    )
    app.config.from_object(Config)
    app.config['TESTING'] = True
    app.secret_key = 'test'
    
    # Importar y registrar todos los blueprints
    from auth.auth import auth
    from autorizar.autorizar import autorizar
    from consulta.consulta import consulta
    from registro.registro import registro
    from reportes.reportes import reportes
    from paginaInicio.paginaInicio import principal
    
    app.register_blueprint(auth)
    app.register_blueprint(autorizar)
    app.register_blueprint(consulta)
    app.register_blueprint(registro)
    app.register_blueprint(reportes)
    app.register_blueprint(principal)
    
    return app


# ══════════════════════════════════════════════════
# FIXTURE: Cliente Flask con sesión simulada
# ══════════════════════════════════════════════════

@pytest.fixture
def cliente_flask(app_flask):
    """Cliente Flask con sesión simulada."""
    with app_flask.test_client() as cliente:
        with cliente.session_transaction() as sesion:
            sesion['id_usuario'] = 1
            sesion['nombre_usuario'] = 'test'
            sesion['nombre_completo'] = 'Test User'
            sesion['rol'] = 'Presidente'
        yield cliente


# ══════════════════════════════════════════════════
# FIXTURE: Mock MySQL
# ══════════════════════════════════════════════════

@pytest.fixture
def mock_mysql(mocker):
    """Mockea mysql en TODOS los módulos."""
    cursor_falso = MagicMock()
    mysql_mock = mocker.patch('extensiones.mysql')
    mysql_mock.connection.cursor.return_value = cursor_falso
    
    _mock_si_existe(mocker, 'auth.auth.mysql', mysql_mock)
    _mock_si_existe(mocker, 'autorizar.autorizar.mysql', mysql_mock)
    _mock_si_existe(mocker, 'consulta.consulta.mysql', mysql_mock)
    _mock_si_existe(mocker, 'registro.registro.mysql', mysql_mock)
    _mock_si_existe(mocker, 'reportes.reportes.mysql', mysql_mock)
    _mock_si_existe(mocker, 'paginaInicio.paginaInicio.mysql', mysql_mock)
    
    return mysql_mock, cursor_falso


# ══════════════════════════════════════════════════
# FIXTURE: Mock Notificar
# ══════════════════════════════════════════════════

@pytest.fixture
def mock_notificar(mocker):
    """Mockea notificar en los módulos que lo importan globalmente."""
    notificar_mock = mocker.patch('extensiones.notificar')
    
    _mock_si_existe(mocker, 'auth.auth.notificar', notificar_mock)
    _mock_si_existe(mocker, 'autorizar.autorizar.notificar', notificar_mock)
    _mock_si_existe(mocker, 'consulta.consulta.notificar', notificar_mock)
    _mock_si_existe(mocker, 'registro.registro.notificar', notificar_mock)
    _mock_si_existe(mocker, 'reportes.reportes.notificar', notificar_mock)
    _mock_si_existe(mocker, 'paginaInicio.paginaInicio.notificar', notificar_mock)
    
    return notificar_mock


# ══════════════════════════════════════════════════
# FIXTURE: Mock Bcrypt
# ══════════════════════════════════════════════════

@pytest.fixture
def mock_bcrypt(mocker):
    """Simula bcrypt para no depender de hashes reales."""
    bcrypt_mock = mocker.patch('extensiones.bcrypt')
    bcrypt_mock.check_password_hash.return_value = True
    bcrypt_mock.generate_password_hash.return_value = b'$2b$12$hash_falso'
    
    _mock_si_existe(mocker, 'auth.auth.bcrypt', bcrypt_mock)
    
    return bcrypt_mock