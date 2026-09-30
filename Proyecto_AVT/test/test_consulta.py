# test/test_consulta.py
# Pruebas unitarias para el módulo consulta/consulta.py


# ══════════════════════════════════════════════════
# PRUEBAS PARA consultaGeneral()
# ══════════════════════════════════════════════════

def test_consulta_general_renderiza(cliente_flask, mocker):
    """GET /consulta/ debe renderizar la plantilla."""
    mocker.patch('consulta.consulta.render_template', return_value='OK')

    respuesta = cliente_flask.get('/consulta/')

    assert respuesta.status_code == 200


# ══════════════════════════════════════════════════
# PRUEBAS PARA consultarRegistro()
# ══════════════════════════════════════════════════

def test_consultar_registro_sin_filtros(cliente_flask, mock_mysql, mocker):
    """GET /consulta/registro sin filtros debe mostrar todos los registros."""
    mysql_mock, cursor = mock_mysql
    cursor.fetchall.return_value = []
    cursor.fetchone.side_effect = [{'total': 10}, {'total': 5}, {'total': 3}]
    mocker.patch('consulta.consulta.render_template', return_value='OK')

    respuesta = cliente_flask.get('/consulta/registro')

    assert respuesta.status_code == 200


def test_consultar_registro_con_filtro_nombre(cliente_flask, mock_mysql, mocker):
    """GET /consulta/registro?nombre=Juan debe filtrar por nombre."""
    mysql_mock, cursor = mock_mysql
    cursor.fetchall.return_value = []
    cursor.fetchone.side_effect = [{'total': 10}, {'total': 5}, {'total': 3}]
    mocker.patch('consulta.consulta.render_template', return_value='OK')

    respuesta = cliente_flask.get('/consulta/registro?nombre=Juan')

    assert respuesta.status_code == 200


# ══════════════════════════════════════════════════
# PRUEBAS PARA consultarAfiliado()
# ══════════════════════════════════════════════════

def test_consultar_afiliado_sin_filtros(cliente_flask, mock_mysql, mocker):
    """GET /consulta/afiliado sin filtros debe mostrar los afiliados."""
    mysql_mock, cursor = mock_mysql
    cursor.fetchall.return_value = []
    cursor.fetchone.side_effect = [{'total': 10}, {'total': 2}]
    mocker.patch('consulta.consulta.render_template', return_value='OK')

    respuesta = cliente_flask.get('/consulta/afiliado')

    assert respuesta.status_code == 200


def test_consultar_afiliado_estatus_todos(cliente_flask, mock_mysql, mocker):
    """GET /consulta/afiliado?estatus=todos debe mostrar todos."""
    mysql_mock, cursor = mock_mysql
    cursor.fetchall.return_value = []
    cursor.fetchone.side_effect = [{'total': 10}, {'total': 2}]
    mocker.patch('consulta.consulta.render_template', return_value='OK')

    respuesta = cliente_flask.get('/consulta/afiliado?estatus=todos')

    assert respuesta.status_code == 200


# ══════════════════════════════════════════════════
# PRUEBAS PARA detalleAfiliado()
# ══════════════════════════════════════════════════

def test_detalle_afiliado_exitoso(cliente_flask, mock_mysql):
    """GET /consulta/afiliado/1 debe devolver los datos del jugador."""
    mysql_mock, cursor = mock_mysql
    cursor.fetchone.return_value = {
        'id_jugador': 1,
        'apellido_paterno': 'Perez',
        'apellido_materno': 'Lopez',
        'nombres': 'Juan',
        'curp': 'PEPJ000101HPLRRN01',
        'fecha_nacimiento': None,
        'celular': '2221234567',
        'telefono': '2221234567',
        'correo_electronico': 'juan@test.com',
        'categoria': 'JUVENIL',
        'id_expediente': 1,
        'estatus_expediente': 'activo'
    }
    cursor.fetchall.return_value = []

    respuesta = cliente_flask.get('/consulta/afiliado/1')

    assert respuesta.status_code == 200
    data = respuesta.get_json()
    assert data['ok'] is True


def test_detalle_afiliado_no_existe(cliente_flask, mock_mysql):
    """GET /consulta/afiliado/999 debe devolver 404."""
    mysql_mock, cursor = mock_mysql
    cursor.fetchone.return_value = None

    respuesta = cliente_flask.get('/consulta/afiliado/999')

    assert respuesta.status_code == 404
    assert respuesta.get_json()['ok'] is False


# ══════════════════════════════════════════════════
# PRUEBAS PARA cambiarCategoria()
# ══════════════════════════════════════════════════

def test_cambiar_categoria_exitoso(cliente_flask, mock_mysql, mock_notificar):
    """POST /consulta/afiliado/1/categoria debe actualizar la categoría."""
    respuesta = cliente_flask.post(
        '/consulta/afiliado/1/categoria',
        json={'categoria': 'JUVENIL'}
    )

    assert respuesta.status_code == 200
    assert respuesta.get_json()['ok'] is True
    mock_notificar.assert_called_once()


def test_cambiar_categoria_vacia(cliente_flask, mock_mysql):
    """POST sin categoría debe devolver 400."""
    respuesta = cliente_flask.post(
        '/consulta/afiliado/1/categoria',
        json={'categoria': ''}
    )

    assert respuesta.status_code == 400
    assert respuesta.get_json()['ok'] is False


def test_cambiar_categoria_error_bd(cliente_flask, mock_mysql):
    """POST con error de BD debe devolver 500."""
    mysql_mock, cursor = mock_mysql
    cursor.execute.side_effect = Exception("Error de BD")

    respuesta = cliente_flask.post(
        '/consulta/afiliado/1/categoria',
        json={'categoria': 'JUVENIL'}
    )

    assert respuesta.status_code == 500


# ══════════════════════════════════════════════════
# PRUEBAS PARA cambiarEstatusAfiliado()
# ══════════════════════════════════════════════════

def test_cambiar_estatus_activo(cliente_flask, mock_mysql, mock_notificar):
    """POST /consulta/afiliado/1/estatus con 'activo' debe funcionar."""
    respuesta = cliente_flask.post(
        '/consulta/afiliado/1/estatus',
        json={'estatus': 'activo'}
    )

    assert respuesta.status_code == 200
    assert respuesta.get_json()['ok'] is True


def test_cambiar_estatus_invalido(cliente_flask, mock_mysql):
    """POST con estatus inválido debe devolver 400."""
    respuesta = cliente_flask.post(
        '/consulta/afiliado/1/estatus',
        json={'estatus': 'invalido'}
    )

    assert respuesta.status_code == 400
    assert respuesta.get_json()['ok'] is False


def test_cambiar_estatus_error_bd(cliente_flask, mock_mysql):
    """POST con error de BD debe devolver 500."""
    mysql_mock, cursor = mock_mysql
    cursor.execute.side_effect = Exception("Error de BD")

    respuesta = cliente_flask.post(
        '/consulta/afiliado/1/estatus',
        json={'estatus': 'activo'}
    )

    assert respuesta.status_code == 500


# ══════════════════════════════════════════════════
# PRUEBAS PARA agregarSancion()
# ══════════════════════════════════════════════════

def test_agregar_sancion_exitoso(cliente_flask, mock_mysql, mock_notificar):
    """POST /consulta/afiliado/1/sancion con datos válidos debe funcionar."""
    mysql_mock, cursor = mock_mysql
    cursor.lastrowid = 1

    respuesta = cliente_flask.post(
        '/consulta/afiliado/1/sancion',
        json={
            'tipo_sancion': 'Suspensión',
            'id_liga': 1,
            'motivo': 'Conducta antideportiva'
        }
    )

    assert respuesta.status_code == 200
    assert respuesta.get_json()['ok'] is True
    mock_notificar.assert_called_once()


def test_agregar_sancion_sin_campos(cliente_flask, mock_mysql):
    """POST sin campos obligatorios debe devolver 400."""
    respuesta = cliente_flask.post(
        '/consulta/afiliado/1/sancion',
        json={'tipo_sancion': '', 'id_liga': None, 'motivo': ''}
    )

    assert respuesta.status_code == 400
    assert respuesta.get_json()['ok'] is False


def test_agregar_sancion_error_bd(cliente_flask, mock_mysql):
    """POST con error de BD debe devolver 500."""
    mysql_mock, cursor = mock_mysql
    cursor.execute.side_effect = Exception("Error de BD")

    respuesta = cliente_flask.post(
        '/consulta/afiliado/1/sancion',
        json={
            'tipo_sancion': 'Suspensión',
            'id_liga': 1,
            'motivo': 'Conducta antideportiva'
        }
    )

    assert respuesta.status_code == 500


# ══════════════════════════════════════════════════
# PRUEBAS PARA consultarLigas()
# ══════════════════════════════════════════════════

def test_consultar_ligas_sin_filtros(cliente_flask, mock_mysql, mocker):
    """GET /consulta/ligas sin filtros debe mostrar todas las ligas."""
    mysql_mock, cursor = mock_mysql
    cursor.fetchall.return_value = []
    cursor.fetchone.side_effect = [
        {'estado': 'activo'},  # tiene_estado
        {'t': 3},              # activas
        {'t': 0},              # inactivas
        {'t': 5},              # total_equipos
        {'t': 10},             # total_jugadores
    ]
    mocker.patch('consulta.consulta.render_template', return_value='OK')

    respuesta = cliente_flask.get('/consulta/ligas')

    assert respuesta.status_code == 200


def test_consultar_ligas_con_filtro(cliente_flask, mock_mysql, mocker):
    """GET /consulta/ligas?nombre=AMIVD debe filtrar por nombre."""
    mysql_mock, cursor = mock_mysql
    cursor.fetchall.return_value = []
    cursor.fetchone.side_effect = [
        {'estado': 'activo'},
        {'t': 3},
        {'t': 0},
        {'t': 5},
        {'t': 10},
    ]
    mocker.patch('consulta.consulta.render_template', return_value='OK')

    respuesta = cliente_flask.get('/consulta/ligas?nombre=AMIVD')

    assert respuesta.status_code == 200


# ══════════════════════════════════════════════════
# PRUEBAS PARA toggleEstadoLiga()
# ══════════════════════════════════════════════════

def test_toggle_estado_liga_exitoso(cliente_flask, mock_mysql, mock_notificar):
    """POST /consulta/ligas/toggle/1 debe cambiar el estado."""
    mysql_mock, cursor = mock_mysql
    cursor.fetchone.return_value = {'estado': 'activo'}

    respuesta = cliente_flask.post('/consulta/ligas/toggle/1')

    assert respuesta.status_code == 200
    data = respuesta.get_json()
    assert data['ok'] is True
    assert data['nuevo_estado'] == 'inactivo'


def test_toggle_estado_liga_no_existe(cliente_flask, mock_mysql):
    """POST /consulta/ligas/toggle/999 debe devolver 404."""
    mysql_mock, cursor = mock_mysql
    cursor.fetchone.return_value = None

    respuesta = cliente_flask.post('/consulta/ligas/toggle/999')

    assert respuesta.status_code == 404
    assert respuesta.get_json()['ok'] is False


def test_toggle_estado_liga_error_bd(cliente_flask, mock_mysql):
    """POST con error de BD debe devolver 500."""
    mysql_mock, cursor = mock_mysql
    cursor.execute.side_effect = Exception("Error de BD")

    respuesta = cliente_flask.post('/consulta/ligas/toggle/1')

    assert respuesta.status_code == 500


# ══════════════════════════════════════════════════
# PRUEBAS PARA consultarEquipo()
# ══════════════════════════════════════════════════

def test_consultar_equipo_sin_filtros(cliente_flask, mock_mysql, mocker):
    """GET /consulta/equipo sin filtros debe mostrar todos los equipos."""
    mysql_mock, cursor = mock_mysql
    cursor.fetchall.return_value = []
    cursor.fetchone.return_value = {'t': 5}
    mocker.patch('consulta.consulta.render_template', return_value='OK')

    respuesta = cliente_flask.get('/consulta/equipo')

    assert respuesta.status_code == 200


def test_consultar_equipo_con_filtro_liga(cliente_flask, mock_mysql, mocker):
    """GET /consulta/equipo?id_liga=1 debe filtrar por liga."""
    mysql_mock, cursor = mock_mysql
    cursor.fetchall.return_value = []
    cursor.fetchone.return_value = {'t': 5}
    mocker.patch('consulta.consulta.render_template', return_value='OK')

    respuesta = cliente_flask.get('/consulta/equipo?id_liga=1')

    assert respuesta.status_code == 200


# ══════════════════════════════════════════════════
# PRUEBAS PARA detalleEquipo()
# ══════════════════════════════════════════════════

def test_detalle_equipo_exitoso(cliente_flask, mock_mysql):
    """GET /consulta/equipo/1 debe devolver los datos del equipo."""
    mysql_mock, cursor = mock_mysql
    cursor.fetchone.return_value = {
        'id_equipo': 1,
        'nombre_equipo': 'TIGRES FC',
        'categoria': 'JUVENIL',
        'estado': 'activo',
        'id_liga': 1,
        'nombre_liga': 'Liga AMIVD Puebla'
    }
    cursor.fetchall.return_value = []

    respuesta = cliente_flask.get('/consulta/equipo/1')

    assert respuesta.status_code == 200
    assert respuesta.get_json()['ok'] is True


def test_detalle_equipo_no_existe(cliente_flask, mock_mysql):
    """GET /consulta/equipo/999 debe devolver 404."""
    mysql_mock, cursor = mock_mysql
    cursor.fetchone.return_value = None

    respuesta = cliente_flask.get('/consulta/equipo/999')

    assert respuesta.status_code == 404
    assert respuesta.get_json()['ok'] is False


# ══════════════════════════════════════════════════
# PRUEBAS PARA cambiarCategoriaEquipo()
# ══════════════════════════════════════════════════

def test_cambiar_categoria_equipo_exitoso(cliente_flask, mock_mysql, mock_notificar):
    """POST /consulta/equipo/1/categoria debe actualizar la categoría."""
    respuesta = cliente_flask.post(
        '/consulta/equipo/1/categoria',
        json={'categoria': 'JUVENIL'}
    )

    assert respuesta.status_code == 200
    assert respuesta.get_json()['ok'] is True


def test_cambiar_categoria_equipo_vacia(cliente_flask, mock_mysql):
    """POST sin categoría debe devolver 400."""
    respuesta = cliente_flask.post(
        '/consulta/equipo/1/categoria',
        json={'categoria': ''}
    )

    assert respuesta.status_code == 400


def test_cambiar_categoria_equipo_error_bd(cliente_flask, mock_mysql):
    """POST con error de BD debe devolver 500."""
    mysql_mock, cursor = mock_mysql
    cursor.execute.side_effect = Exception("Error de BD")

    respuesta = cliente_flask.post(
        '/consulta/equipo/1/categoria',
        json={'categoria': 'JUVENIL'}
    )

    assert respuesta.status_code == 500


# ══════════════════════════════════════════════════
# PRUEBAS PARA toggleEstadoEquipo()
# ══════════════════════════════════════════════════

def test_toggle_estado_equipo_exitoso(cliente_flask, mock_mysql, mock_notificar):
    """POST /consulta/equipo/1/estado debe cambiar el estado."""
    mysql_mock, cursor = mock_mysql
    cursor.fetchone.return_value = {'estado': 'activo'}

    respuesta = cliente_flask.post('/consulta/equipo/1/estado')

    assert respuesta.status_code == 200
    data = respuesta.get_json()
    assert data['ok'] is True
    assert data['nuevo_estado'] == 'inactivo'


def test_toggle_estado_equipo_no_existe(cliente_flask, mock_mysql):
    """POST /consulta/equipo/999/estado debe devolver 404."""
    mysql_mock, cursor = mock_mysql
    cursor.fetchone.return_value = None

    respuesta = cliente_flask.post('/consulta/equipo/999/estado')

    assert respuesta.status_code == 404


def test_toggle_estado_equipo_error_bd(cliente_flask, mock_mysql):
    """POST con error de BD debe devolver 500."""
    mysql_mock, cursor = mock_mysql
    cursor.execute.side_effect = Exception("Error de BD")

    respuesta = cliente_flask.post('/consulta/equipo/1/estado')

    assert respuesta.status_code == 500


# ══════════════════════════════════════════════════
# PRUEBAS PARA consultarPagos()
# ══════════════════════════════════════════════════

def test_consultar_pagos_sin_filtros(cliente_flask, mock_mysql, mocker):
    """GET /consulta/pagos sin filtros debe mostrar todos los pagos."""
    mysql_mock, cursor = mock_mysql
    cursor.fetchall.return_value = []
    cursor.fetchone.side_effect = [{'t': 5}, {'t': 3}, {'t': 1}]
    mocker.patch('consulta.consulta.render_template', return_value='OK')

    respuesta = cliente_flask.get('/consulta/pagos')

    assert respuesta.status_code == 200


def test_consultar_pagos_con_filtro_estatus(cliente_flask, mock_mysql, mocker):
    """GET /consulta/pagos?estatus=Completado debe filtrar."""
    mysql_mock, cursor = mock_mysql
    cursor.fetchall.return_value = []
    cursor.fetchone.side_effect = [{'t': 5}, {'t': 3}, {'t': 1}]
    mocker.patch('consulta.consulta.render_template', return_value='OK')

    respuesta = cliente_flask.get('/consulta/pagos?estatus=Completado')

    assert respuesta.status_code == 200


# ══════════════════════════════════════════════════
# PRUEBAS PARA consultarTutor()
# ══════════════════════════════════════════════════

def test_consultar_tutor_sin_filtros(cliente_flask, mock_mysql, mocker):
    """GET /consulta/tutor sin filtros debe mostrar todos los tutores."""
    mysql_mock, cursor = mock_mysql
    cursor.fetchall.return_value = []
    cursor.fetchone.side_effect = [{'t': 2}, {'t': 2}, {'t': 1}]
    mocker.patch('consulta.consulta.render_template', return_value='OK')

    respuesta = cliente_flask.get('/consulta/tutor')

    assert respuesta.status_code == 200


def test_consultar_tutor_con_filtro_nombre(cliente_flask, mock_mysql, mocker):
    """GET /consulta/tutor?nombre_tutor=ALAN debe filtrar."""
    mysql_mock, cursor = mock_mysql
    cursor.fetchall.return_value = []
    cursor.fetchone.side_effect = [{'t': 2}, {'t': 2}, {'t': 1}]
    mocker.patch('consulta.consulta.render_template', return_value='OK')

    respuesta = cliente_flask.get('/consulta/tutor?nombre_tutor=ALAN')

    assert respuesta.status_code == 200


# ══════════════════════════════════════════════════
# PRUEBAS PARA contadores_ligas()
# ══════════════════════════════════════════════════

def test_contadores_ligas_exitoso(cliente_flask, mock_mysql):
    """GET /consulta/contadores-ligas debe devolver los contadores."""
    mysql_mock, cursor = mock_mysql
    cursor.fetchone.side_effect = [
        {'estado': 'activo'},  # tiene_estado
        {'t': 3},              # activas
        {'t': 0},              # inactivas
        {'t': 5},              # total_equipos
        {'t': 10},             # total_jugadores
    ]

    respuesta = cliente_flask.get('/consulta/contadores-ligas')

    assert respuesta.status_code == 200
    data = respuesta.get_json()
    assert data['activas'] == 3
    assert data['inactivas'] == 0


def test_contadores_ligas_sin_login(app_flask):
    """GET /consulta/contadores-ligas sin sesión debe redirigir."""
    with app_flask.test_client() as cliente:
        respuesta = cliente.get('/consulta/contadores-ligas')

    assert respuesta.status_code == 302