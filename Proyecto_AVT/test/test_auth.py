# test/test_auth.py 
# Pruebas unitarias para el módulo auth/auth.py
#Total de 22 pruebas unitarias, cubriendo todas las rutas y funciones principales.

# ══════════════════════════════════════════════════
# PRUEBAS PARA index()
# ══════════════════════════════════════════════════

def test_index_renderiza_login(cliente_flask, mocker):
    """GET / debe renderizar la plantilla de login."""
    mocker.patch('auth.auth.render_template', return_value='LOGIN OK')

    respuesta = cliente_flask.get('/iniciarSesion')

    assert respuesta.status_code == 200


# ══════════════════════════════════════════════════
# PRUEBAS PARA iniciarSesion()
# ══════════════════════════════════════════════════

def test_iniciar_sesion_exitoso(cliente_flask, mock_mysql, mock_bcrypt, mock_notificar):
    """Login con credenciales válidas debe redirigir a paginaInicio."""
    mysql_mock, cursor = mock_mysql
    cursor.fetchone.return_value = {
        'id_usuario': 1,
        'nombre_usuario': 'presidente',
        'password': '$2b$12$hash',
        'nombre_completo': 'Juan Perez',
        'rol': 'Presidente',
        'activo': 1
    }
    mock_bcrypt.check_password_hash.return_value = True

    respuesta = cliente_flask.post('/iniciarSesion', data={
        'nombreUsuario': 'presidente',
        'password': 'password123'
    })

    assert respuesta.status_code == 302
    assert 'paginaInicio' in respuesta.headers['Location']


def test_iniciar_sesion_usuario_inexistente(cliente_flask, mock_mysql):
    """Login con usuario inexistente debe mostrar 'El usuario no existe'."""
    mysql_mock, cursor = mock_mysql
    cursor.fetchone.return_value = None

    respuesta = cliente_flask.post('/iniciarSesion', data={
        'nombreUsuario': 'noexiste',
        'password': 'password123'
    }, follow_redirects=True)

    assert respuesta.status_code == 200
    assert b'El usuario no existe' in respuesta.data


def test_iniciar_sesion_password_incorrecta(cliente_flask, mock_mysql, mock_bcrypt):
    """Login con contraseña incorrecta debe mostrar 'La contraseña es incorrecta'."""
    mysql_mock, cursor = mock_mysql
    cursor.fetchone.return_value = {
        'id_usuario': 1,
        'nombre_usuario': 'presidente',
        'password': '$2b$12$hash',
        'nombre_completo': 'Juan Perez',
        'rol': 'Presidente',
        'activo': 1
    }
    mock_bcrypt.check_password_hash.return_value = False

    respuesta = cliente_flask.post('/iniciarSesion', data={
        'nombreUsuario': 'presidente',
        'password': 'incorrecta'
    }, follow_redirects=True)

    assert respuesta.status_code == 200
    assert b'La contrase' in respuesta.data


def test_iniciar_sesion_usuario_inactivo(cliente_flask, mock_mysql):
    """Login con usuario inactivo debe mostrar 'El usuario est'."""
    mysql_mock, cursor = mock_mysql
    cursor.fetchone.return_value = {
        'id_usuario': 1,
        'nombre_usuario': 'presidente',
        'password': '$2b$12$hash',
        'nombre_completo': 'Juan Perez',
        'rol': 'Presidente',
        'activo': 0
    }

    respuesta = cliente_flask.post('/iniciarSesion', data={
        'nombreUsuario': 'presidente',
        'password': 'password123'
    }, follow_redirects=True)

    assert respuesta.status_code == 200
    assert b'inactivo' in respuesta.data


# ══════════════════════════════════════════════════
# PRUEBAS PARA nuevoUsuario()
# ══════════════════════════════════════════════════

def test_nuevo_usuario_get(cliente_flask, mocker):
    """GET /nuevoUsuario debe renderizar el formulario."""
    mocker.patch('auth.auth.render_template', return_value='FORM OK')

    respuesta = cliente_flask.get('/nuevoUsuario')

    assert respuesta.status_code == 200


def test_nuevo_usuario_exitoso(cliente_flask, mock_mysql, mock_bcrypt, mock_notificar):
    """POST /nuevoUsuario con datos válidos debe crear el usuario."""
    mysql_mock, cursor = mock_mysql
    # Primera llamada: verificar nombre_usuario (no existe)
    # Segunda llamada: verificar email (no existe)
    cursor.fetchone.side_effect = [None, None]
    cursor.lastrowid = 5

    respuesta = cliente_flask.post('/nuevoUsuario', data={
        'nombre_usuario': 'nuevo',
        'nombre_completo': 'Juan Perez',
        'email': 'juan@test.com',
        'password': 'Password1',
        'rol': 'Administrador'
    }, follow_redirects=True)

    assert respuesta.status_code == 200


def test_nuevo_usuario_rol_invalido(cliente_flask, mock_mysql):
    """POST /nuevoUsuario con rol inválido debe mostrar 'Rol inválido'."""
    respuesta = cliente_flask.post('/nuevoUsuario', data={
        'nombre_usuario': 'nuevo',
        'nombre_completo': 'Juan Perez',
        'email': 'juan@test.com',
        'password': 'Password1',
        'rol': 'Delegado'
    }, follow_redirects=True)

    assert respuesta.status_code == 200
    assert b'Rol inv' in respuesta.data


def test_nuevo_usuario_nombre_duplicado(cliente_flask, mock_mysql):
    """POST /nuevoUsuario con nombre duplicado debe mostrar 'El nombre de usuario ya est'."""
    mysql_mock, cursor = mock_mysql
    # Primera llamada: nombre_usuario existe
    cursor.fetchone.return_value = {'id_usuario': 1}

    respuesta = cliente_flask.post('/nuevoUsuario', data={
        'nombre_usuario': 'presidente',
        'nombre_completo': 'Juan Perez',
        'email': 'juan@test.com',
        'password': 'Password1',
        'rol': 'Administrador'
    }, follow_redirects=True)

    assert respuesta.status_code == 200
    assert b'nombre de usuario ya est' in respuesta.data


def test_nuevo_usuario_email_duplicado(cliente_flask, mock_mysql):
    """POST /nuevoUsuario con email duplicado debe mostrar 'El correo electr'."""
    mysql_mock, cursor = mock_mysql
    # Primera llamada: nombre_usuario NO existe
    # Segunda llamada: email SÍ existe
    cursor.fetchone.side_effect = [None, {'id_usuario': 1}]

    respuesta = cliente_flask.post('/nuevoUsuario', data={
        'nombre_usuario': 'nuevo',
        'nombre_completo': 'Juan Perez',
        'email': 'presidente@test.com',
        'password': 'Password1',
        'rol': 'Administrador'
    }, follow_redirects=True)

    assert respuesta.status_code == 200
    assert b'correo electr' in respuesta.data


# ══════════════════════════════════════════════════
# PRUEBAS PARA cerrarSesion()
# ══════════════════════════════════════════════════

def test_cerrar_sesion(cliente_flask):
    """GET /cerrarSesion debe limpiar la sesión y redirigir."""
    respuesta = cliente_flask.get('/cerrarSesion')

    assert respuesta.status_code == 302
    assert 'iniciarSesion' in respuesta.headers['Location']


# ══════════════════════════════════════════════════
# PRUEBAS PARA generar_numero_registro()
# ══════════════════════════════════════════════════

def test_generar_numero_registro_jugador(mock_mysql):
    """Genera JUG-001 si no hay jugadores."""
    from auth.auth import generar_numero_registro
    mysql_mock, cursor = mock_mysql
    cursor.fetchone.return_value = {'ultimo': None}

    resultado = generar_numero_registro(cursor, 'jugador')

    assert resultado == 'JUG-001'


def test_generar_numero_registro_tipo_invalido(mock_mysql):
    """Tipo inválido debe lanzar ValueError."""
    from auth.auth import generar_numero_registro
    mysql_mock, cursor = mock_mysql

    try:
        generar_numero_registro(cursor, 'invalido')
        assert False, "Debería lanzar ValueError"
    except ValueError:
        assert True


# ══════════════════════════════════════════════════
# PRUEBAS PARA accesoExterno()
# ══════════════════════════════════════════════════

def test_acceso_externo_get(cliente_flask, mocker):
    """GET /accesoExterno debe renderizar el formulario."""
    mocker.patch('auth.auth.render_template', return_value='ACCESO OK')

    respuesta = cliente_flask.get('/accesoExterno')

    assert respuesta.status_code == 200


# ══════════════════════════════════════════════════
# PRUEBAS PARA accesoExternoPost()
# ══════════════════════════════════════════════════

def test_acceso_externo_post_campos_vacios(cliente_flask):
    """POST /accesoExterno sin campos debe mostrar 'Nombre y correo son obligatorios'."""
    respuesta = cliente_flask.post('/accesoExterno', data={
        'nombre_completo': '',
        'email': ''
    }, follow_redirects=True)

    assert respuesta.status_code == 200
    assert b'obligatorios' in respuesta.data


def test_acceso_externo_post_exitoso(cliente_flask):
    """POST /accesoExterno con datos válidos debe redirigir a formularioExterno."""
    respuesta = cliente_flask.post('/accesoExterno', data={
        'nombre_completo': 'Juan Perez',
        'email': 'juan@test.com'
    })

    assert respuesta.status_code == 302
    assert 'registroExterno' in respuesta.headers['Location']


# ══════════════════════════════════════════════════
# PRUEBAS PARA formularioExterno()
# ══════════════════════════════════════════════════

def test_formulario_externo_sin_sesion(cliente_flask):
    """GET /registroExterno sin sesión ext debe redirigir a accesoExterno."""
    with cliente_flask.session_transaction() as sesion:
        sesion.pop('ext_nombre', None)

    respuesta = cliente_flask.get('/registroExterno')

    assert respuesta.status_code == 302
    assert 'accesoExterno' in respuesta.headers['Location']


def test_formulario_externo_con_sesion(cliente_flask, mock_mysql, mocker):
    """GET /registroExterno con sesión debe renderizar el formulario."""
    mysql_mock, cursor = mock_mysql
    cursor.fetchall.return_value = []
    mocker.patch('auth.auth.render_template', return_value='FORM OK')

    with cliente_flask.session_transaction() as sesion:
        sesion['ext_nombre'] = 'Juan Perez'
        sesion['ext_email'] = 'juan@test.com'

    respuesta = cliente_flask.get('/registroExterno')

    assert respuesta.status_code == 200


# ══════════════════════════════════════════════════
# PRUEBAS PARA siguienteRegistroExterno()
# ══════════════════════════════════════════════════

def test_siguiente_registro_jugador(cliente_flask, mock_mysql):
    """GET /registro-externo/siguiente_registro?tipo=jugador debe devolver JUG-XXX."""
    mysql_mock, cursor = mock_mysql
    cursor.fetchone.return_value = {'total': 5}

    respuesta = cliente_flask.get('/registro-externo/siguiente_registro?tipo=jugador')

    assert respuesta.status_code == 200
    assert respuesta.get_json()['ok'] is True
    assert respuesta.get_json()['numero'] == 'JUG-006'


def test_siguiente_registro_entrenador(cliente_flask, mock_mysql):
    """GET /registro-externo/siguiente_registro?tipo=entrenador debe devolver ENT-XXX."""
    mysql_mock, cursor = mock_mysql
    cursor.fetchone.return_value = {'total': 2}

    respuesta = cliente_flask.get('/registro-externo/siguiente_registro?tipo=entrenador')

    assert respuesta.status_code == 200
    assert respuesta.get_json()['numero'] == 'ENT-003'


def test_siguiente_registro_tipo_invalido(cliente_flask, mock_mysql):
    """GET con tipo inválido debe devolver 400."""
    mysql_mock, cursor = mock_mysql

    respuesta = cliente_flask.get('/registro-externo/siguiente_registro?tipo=invalido')

    assert respuesta.status_code == 400


# ══════════════════════════════════════════════════
# PRUEBAS PARA registroExitoso()
# ══════════════════════════════════════════════════

def test_registro_exitoso(cliente_flask, mocker):
    """GET /registroExitoso debe renderizar la pantalla de éxito."""
    mocker.patch('auth.auth.render_template', return_value='EXITO OK')

    respuesta = cliente_flask.get('/registroExitoso')

    assert respuesta.status_code == 200