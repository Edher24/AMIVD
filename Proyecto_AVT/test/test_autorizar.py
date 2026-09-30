# test/test_autorizar.py
# Pruebas unitarias para el módulo autorizar/autorizar.py


# ══════════════════════════════════════════════════
# PRUEBAS PARA autorizarRegistro()
# ══════════════════════════════════════════════════

def test_autorizar_registro_renderiza(cliente_flask, mock_mysql, mocker):
    """GET /autorizar/ debe renderizar la plantilla con contadores y solicitudes."""
    mysql_mock, cursor = mock_mysql

    # Primera llamada: contadores. Segunda: solicitudes.
    cursor.fetchone.return_value = {'pendientes': 3, 'hoy': 1, 'rechazadas': 0}
    cursor.fetchall.return_value = [
        {'id_autorizacion': 1, 'tipo_solicitud': 'jugador', 'nombre_persona': 'Juan Pérez'}
    ]

    mocker.patch('autorizar.autorizar.render_template', return_value='OK')

    respuesta = cliente_flask.get('/autorizar/')

    assert respuesta.status_code == 200


def test_autorizar_registro_sin_login(app_flask):
    """GET /autorizar/ sin sesión debe redirigir al login."""
    with app_flask.test_client() as cliente:
        # NO agregamos id_usuario a la sesión
        respuesta = cliente.get('/autorizar/')

    assert respuesta.status_code == 302
    assert 'iniciarSesion' in respuesta.headers['Location']


def test_autorizar_registro_sin_solicitudes(cliente_flask, mock_mysql, mocker):
    """GET /autorizar/ sin solicitudes debe renderizar igual."""
    mysql_mock, cursor = mock_mysql

    cursor.fetchone.return_value = {'pendientes': 0, 'hoy': 0, 'rechazadas': 0}
    cursor.fetchall.return_value = []

    mocker.patch('autorizar.autorizar.render_template', return_value='OK')

    respuesta = cliente_flask.get('/autorizar/')

    assert respuesta.status_code == 200


# ══════════════════════════════════════════════════
# PRUEBAS PARA contadores()
# ══════════════════════════════════════════════════

def test_contadores_devuelve_json(cliente_flask, mock_mysql):
    """GET /autorizar/contadores debe devolver los contadores en JSON."""
    mysql_mock, cursor = mock_mysql
    cursor.fetchone.return_value = {'pendientes': 5, 'hoy': 2, 'rechazadas': 1}

    respuesta = cliente_flask.get('/autorizar/contadores')

    assert respuesta.status_code == 200
    data = respuesta.get_json()
    assert data['pendientes'] == 5
    assert data['hoy'] == 2
    assert data['rechazadas'] == 1


def test_contadores_sin_login(app_flask):
    """GET /autorizar/contadores sin sesión debe redirigir al login."""
    with app_flask.test_client() as cliente:
        # NO agregamos id_usuario a la sesión
        respuesta = cliente.get('/autorizar/contadores')

    assert respuesta.status_code == 302


# ══════════════════════════════════════════════════
# PRUEBAS PARA aprobar()
# ══════════════════════════════════════════════════

def test_aprobar_exitoso(cliente_flask, mock_mysql, mock_notificar):
    """Aprobar una solicitud existente debe devolver ok=True."""
    mysql_mock, cursor = mock_mysql
    cursor.fetchone.return_value = {
        'tipo_solicitud': 'jugador',
        'id_referencia': 10
    }

    respuesta = cliente_flask.post('/autorizar/aprobar/1')

    assert respuesta.status_code == 200
    assert respuesta.get_json()['ok'] is True
    mock_notificar.assert_called_once()


def test_aprobar_solicitud_no_existe(cliente_flask, mock_mysql):
    """Aprobar una solicitud inexistente debe devolver 404."""
    mysql_mock, cursor = mock_mysql
    cursor.fetchone.return_value = None

    respuesta = cliente_flask.post('/autorizar/aprobar/999')

    assert respuesta.status_code == 404
    assert respuesta.get_json()['ok'] is False


def test_aprobar_error_en_bd(cliente_flask, mock_mysql):
    """Si la BD lanza error, debe hacer rollback y devolver 500."""
    mysql_mock, cursor = mock_mysql
    cursor.fetchone.side_effect = Exception("Error de BD")

    respuesta = cliente_flask.post('/autorizar/aprobar/1')

    assert respuesta.status_code == 500
    mysql_mock.connection.rollback.assert_called_once()


# ══════════════════════════════════════════════════
# PRUEBAS PARA rechazar()
# ══════════════════════════════════════════════════

def test_rechazar_sin_comentario(cliente_flask, mock_mysql):
    """Rechazar sin comentario debe devolver 400."""
    respuesta = cliente_flask.post('/autorizar/rechazar/1', data={'comentario': ''})

    assert respuesta.status_code == 400
    assert 'comentario' in respuesta.get_json()['mensaje'].lower()


def test_rechazar_exitoso(cliente_flask, mock_mysql, mock_notificar):
    """Rechazar con comentario válido debe devolver ok=True."""
    mysql_mock, cursor = mock_mysql
    cursor.fetchone.return_value = {
        'tipo_solicitud': 'entrenador',
        'id_referencia': 5
    }

    respuesta = cliente_flask.post(
        '/autorizar/rechazar/1',
        data={'comentario': 'Documentación incompleta'}
    )

    assert respuesta.status_code == 200
    assert respuesta.get_json()['ok'] is True
    mock_notificar.assert_called_once()


def test_rechazar_solicitud_no_existe(cliente_flask, mock_mysql):
    """Rechazar una solicitud inexistente debe devolver 404."""
    mysql_mock, cursor = mock_mysql
    cursor.fetchone.return_value = None

    respuesta = cliente_flask.post(
        '/autorizar/rechazar/999',
        data={'comentario': 'Motivo válido'}
    )

    assert respuesta.status_code == 404