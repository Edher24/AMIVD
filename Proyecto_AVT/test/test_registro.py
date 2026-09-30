# test/test_registro.py
import pytest


# ══════════════════════════════════════════════════
# LIGA
# ══════════════════════════════════════════════════

def test_guardar_liga_exitoso(cliente_flask, mock_mysql, mock_notificar):
    """POST /registro/liga/guardar con datos válidos debe registrar la liga."""
    mysql_mock, cursor = mock_mysql

    # No existe liga con ese nombre
    cursor.fetchone.return_value = None
    cursor.lastrowid = 42

    respuesta = cliente_flask.post(
        '/registro/liga/guardar',
        data={'nombre_liga': 'liga premier', 'categoria': 'varonil'}
    )

    assert respuesta.status_code == 200
    data = respuesta.get_json()
    assert data['ok'] is True
    assert data['nombre'] == 'LIGA PREMIER'
    assert data['categoria'] == 'VARONIL'
    assert data['id'] == 42


def test_guardar_liga_sin_nombre(cliente_flask, mock_mysql):
    """POST sin nombre debe devolver 400."""
    respuesta = cliente_flask.post(
        '/registro/liga/guardar',
        data={'nombre_liga': '   ', 'categoria': 'VARONIL'}
    )

    assert respuesta.status_code == 400
    assert respuesta.get_json()['ok'] is False


def test_guardar_liga_duplicada(cliente_flask, mock_mysql):
    """POST con liga ya existente debe devolver 400."""
    mysql_mock, cursor = mock_mysql
    cursor.fetchone.return_value = {'id_liga': 1}  # ya existe

    respuesta = cliente_flask.post(
        '/registro/liga/guardar',
        data={'nombre_liga': 'LIGA PREMIER', 'categoria': 'VARONIL'}
    )

    assert respuesta.status_code == 400
    assert 'ya existe' in respuesta.get_json()['mensaje'].lower()


def test_eliminar_liga_exitoso(cliente_flask, mock_mysql, mock_notificar):
    """POST /registro/liga/eliminar/<id> debe devolver ok=True."""
    mysql_mock, cursor = mock_mysql

    respuesta = cliente_flask.post('/registro/liga/eliminar/1')

    assert respuesta.status_code == 200
    assert respuesta.get_json()['ok'] is True


# ══════════════════════════════════════════════════
# EQUIPO
# ══════════════════════════════════════════════════

def test_guardar_equipo_exitoso(cliente_flask, mock_mysql, mock_notificar):
    """POST /registro/equipo/guardar con datos válidos debe registrar el equipo."""
    mysql_mock, cursor = mock_mysql

    # Primera llamada: verificar duplicado (None)
    # Segunda llamada: obtener nombre de liga
    cursor.fetchone.side_effect = [
        None,
        {'nombre_liga': 'LIGA PREMIER'}
    ]
    cursor.lastrowid = 7

    respuesta = cliente_flask.post(
        '/registro/equipo/guardar',
        data={'nombre_equipo': 'aguilas', 'id_liga': '1', 'categoria': 'JUVENIL'}
    )

    assert respuesta.status_code == 200
    data = respuesta.get_json()
    assert data['ok'] is True
    assert data['nombre'] == 'AGUILAS'
    assert data['nombre_liga'] == 'LIGA PREMIER'


def test_guardar_equipo_datos_incompletos(cliente_flask, mock_mysql):
    """POST sin nombre o sin liga debe devolver 400."""
    respuesta = cliente_flask.post(
        '/registro/equipo/guardar',
        data={'nombre_equipo': '', 'id_liga': ''}
    )

    assert respuesta.status_code == 400
    assert respuesta.get_json()['ok'] is False


def test_guardar_equipo_duplicado(cliente_flask, mock_mysql):
    """POST con equipo ya existente en la liga debe devolver 400."""
    mysql_mock, cursor = mock_mysql
    cursor.fetchone.return_value = {'id_equipo': 1}  # ya existe

    respuesta = cliente_flask.post(
        '/registro/equipo/guardar',
        data={'nombre_equipo': 'AGUILAS', 'id_liga': '1', 'categoria': 'JUVENIL'}
    )

    assert respuesta.status_code == 400
    assert 'ya existe' in respuesta.get_json()['mensaje'].lower()


def test_eliminar_equipo_exitoso(cliente_flask, mock_mysql, mock_notificar):
    """POST /registro/equipo/eliminar/<id> debe devolver ok=True."""
    mysql_mock, cursor = mock_mysql

    respuesta = cliente_flask.post('/registro/equipo/eliminar/5')

    assert respuesta.status_code == 200
    assert respuesta.get_json()['ok'] is True


# ══════════════════════════════════════════════════
# PAGO
# ══════════════════════════════════════════════════

def test_guardar_pago_datos_incompletos(cliente_flask, mock_mysql):
    """POST sin jugador o sin fecha debe devolver 400."""
    respuesta = cliente_flask.post(
        '/registro/pago/guardar',
        data={'id_persona': '', 'fecha_pago': ''}
    )

    assert respuesta.status_code == 400
    assert respuesta.get_json()['ok'] is False


def test_guardar_pago_nuevo(cliente_flask, mock_mysql, mock_notificar):
    """POST con datos válidos y sin pago previo debe insertar uno nuevo."""
    mysql_mock, cursor = mock_mysql

    # 1ª: afiliación existente. 2ª: no hay pago previo.
    cursor.fetchone.side_effect = [
        {'id_afiliacion': 10},
        None
    ]
    cursor.lastrowid = 99

    respuesta = cliente_flask.post(
        '/registro/pago/guardar',
        data={
            'id_persona': '1',
            'fecha_pago': '2026-04-01',
            'estatus': 'Pendiente',
            'metodo_pago': 'EFECTIVO',
            'referencia': 'REF-001'
        }
    )

    assert respuesta.status_code == 200
    data = respuesta.get_json()
    assert data['ok'] is True
    assert data['id'] == 99
    assert 'registrado' in data['mensaje'].lower()


def test_guardar_pago_existente_actualiza(cliente_flask, mock_mysql, mock_notificar):
    """POST con pago ya existente debe actualizarlo, no duplicarlo."""
    mysql_mock, cursor = mock_mysql

    # 1ª: afiliación existente. 2ª: pago ya existe.
    cursor.fetchone.side_effect = [
        {'id_afiliacion': 10},
        {'id_pago': 55}
    ]

    respuesta = cliente_flask.post(
        '/registro/pago/guardar',
        data={
            'id_persona': '1',
            'fecha_pago': '2026-04-01',
            'estatus': 'Completado',
            'metodo_pago': 'TRANSFERENCIA'
        }
    )

    assert respuesta.status_code == 200
    data = respuesta.get_json()
    assert data['ok'] is True
    assert data['id'] == 55
    assert 'actualizado' in data['mensaje'].lower()


def test_actualizar_pago_estatus_invalido(cliente_flask, mock_mysql):
    """POST con estatus no permitido debe devolver 400."""
    respuesta = cliente_flask.post(
        '/registro/pago/actualizar/1',
        data={'estatus': 'INVENTADO'}
    )

    assert respuesta.status_code == 400
    assert 'inválido' in respuesta.get_json()['mensaje'].lower()


def test_actualizar_pago_exitoso(cliente_flask, mock_mysql, mock_notificar):
    """POST con estatus válido debe actualizar el pago."""
    mysql_mock, cursor = mock_mysql

    respuesta = cliente_flask.post(
        '/registro/pago/actualizar/1',
        data={'estatus': 'Completado'}
    )

    assert respuesta.status_code == 200
    assert respuesta.get_json()['ok'] is True


# ══════════════════════════════════════════════════
# SIGUIENTE REGISTRO
# ══════════════════════════════════════════════════

def test_siguiente_registro_tipo_invalido(cliente_flask, mock_mysql):
    """GET con tipo desconocido debe devolver 400."""
    respuesta = cliente_flask.get('/registro/persona/siguiente_registro?tipo=inventado')

    assert respuesta.status_code == 400
    assert respuesta.get_json()['ok'] is False


def test_siguiente_registro_jugador(cliente_flask, mock_mysql):
    """GET con tipo=jugador debe devolver el siguiente número JUG-XXX."""
    mysql_mock, cursor = mock_mysql
    cursor.fetchone.return_value = {'total': 5}

    respuesta = cliente_flask.get('/registro/persona/siguiente_registro?tipo=jugador')

    assert respuesta.status_code == 200
    data = respuesta.get_json()
    assert data['ok'] is True
    assert data['numero'] == 'JUG-006'


# ══════════════════════════════════════════════════
# GENERAR NÚMERO DE REGISTRO (función pura)
# ══════════════════════════════════════════════════

def test_generar_numero_registro_jugador(mock_mysql):
    """generar_numero_registro debe devolver JUG-XXX con el siguiente número."""
    from registro.registro import generar_numero_registro
    mysql_mock, cursor = mock_mysql
    cursor.fetchone.return_value = {'ultimo': 7}

    resultado = generar_numero_registro(cursor, 'jugador')

    assert resultado == 'JUG-008'


def test_generar_numero_registro_entrenador(mock_mysql):
    """generar_numero_registro con entrenador debe devolver ENT-XXX."""
    from registro.registro import generar_numero_registro
    mysql_mock, cursor = mock_mysql
    cursor.fetchone.return_value = {'ultimo': 0}

    resultado = generar_numero_registro(cursor, 'entrenador')

    assert resultado == 'ENT-001'


def test_generar_numero_registro_tipo_invalido(mock_mysql):
    """generar_numero_registro con tipo desconocido debe lanzar ValueError."""
    from registro.registro import generar_numero_registro
    mysql_mock, cursor = mock_mysql

    with pytest.raises(ValueError, match="Tipo inválido"):
        generar_numero_registro(cursor, 'inventado')