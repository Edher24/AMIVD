# test/test_paginaInicio.py
# Pruebas unitarias para el módulo paginaInicio/paginaInicio.py


# ══════════════════════════════════════════════════
# PRUEBAS PARA paginaInicio()
# ══════════════════════════════════════════════════

def test_pagina_inicio_renderiza(cliente_flask, mocker):
    """GET /paginaInicio debe renderizar la plantilla."""
    mocker.patch('paginaInicio.paginaInicio.render_template', return_value='OK')

    respuesta = cliente_flask.get('/paginaInicio')

    assert respuesta.status_code == 200


# ══════════════════════════════════════════════════
# PRUEBAS PARA notificaciones()
# ══════════════════════════════════════════════════

def test_notificaciones_sin_filtro(cliente_flask, mock_mysql, mocker):
    """GET /notificaciones sin filtro debe mostrar todas las notificaciones."""
    mysql_mock, cursor = mock_mysql
    cursor.fetchall.return_value = []
    mocker.patch('paginaInicio.paginaInicio.render_template', return_value='OK')

    respuesta = cliente_flask.get('/notificaciones')

    assert respuesta.status_code == 200


def test_notificaciones_con_filtro_fecha(cliente_flask, mock_mysql, mocker):
    """GET /notificaciones?fecha=2026-05-04 debe filtrar por fecha."""
    mysql_mock, cursor = mock_mysql
    cursor.fetchall.return_value = []
    mocker.patch('paginaInicio.paginaInicio.render_template', return_value='OK')

    respuesta = cliente_flask.get('/notificaciones?fecha=2026-05-04')

    assert respuesta.status_code == 200


# ══════════════════════════════════════════════════
# PRUEBAS PARA marcar_todas_leidas()
# ══════════════════════════════════════════════════

def test_marcar_todas_leidas(cliente_flask, mock_mysql):
    """POST /notificaciones/marcar_todas debe devolver ok=True."""
    respuesta = cliente_flask.post('/notificaciones/marcar_todas')

    assert respuesta.status_code == 200
    assert respuesta.get_json()['ok'] is True


# ══════════════════════════════════════════════════
# PRUEBAS PARA marcar_leida()
# ══════════════════════════════════════════════════

def test_marcar_leida(cliente_flask, mock_mysql):
    """POST /notificaciones/marcar/1 debe devolver ok=True."""
    respuesta = cliente_flask.post('/notificaciones/marcar/1')

    assert respuesta.status_code == 200
    assert respuesta.get_json()['ok'] is True


# ══════════════════════════════════════════════════
# PRUEBAS PARA digitalizar()
# ══════════════════════════════════════════════════

def test_digitalizar_renderiza(cliente_flask, mock_mysql, mocker):
    """GET /digitalizarDocumentos debe renderizar la plantilla."""
    mysql_mock, cursor = mock_mysql
    cursor.fetchall.return_value = []
    mocker.patch('paginaInicio.paginaInicio.render_template', return_value='OK')

    respuesta = cliente_flask.get('/digitalizarDocumentos')

    assert respuesta.status_code == 200


# ══════════════════════════════════════════════════
# PRUEBAS PARA subir_documento()
# ══════════════════════════════════════════════════

def test_subir_documento_sin_datos(cliente_flask, mock_mysql):
    """POST /digitalizarDocumentos/subir sin datos debe devolver 400."""
    respuesta = cliente_flask.post('/digitalizarDocumentos/subir', data={})

    assert respuesta.status_code == 400
    assert respuesta.get_json()['ok'] is False


def test_subir_documento_formato_invalido(cliente_flask, mock_mysql):
    """POST con archivo .txt debe devolver 400."""
    from io import BytesIO
    archivo_falso = (BytesIO(b'contenido'), 'documento.txt')

    respuesta = cliente_flask.post(
        '/digitalizarDocumentos/subir',
        data={
            'tipoDocumento': 'ine',
            'id_persona': '1',
            'archivo': archivo_falso
        },
        content_type='multipart/form-data'
    )

    assert respuesta.status_code == 400
    assert b'Solo PNG' in respuesta.data or 'Solo PNG' in respuesta.get_json().get('mensaje', '')


def test_subir_documento_exitoso(cliente_flask, mock_mysql, mock_notificar, tmp_path, mocker):
    """POST con datos válidos debe subir el documento."""
    from io import BytesIO
    mysql_mock, cursor = mock_mysql
    cursor.fetchone.return_value = {'nombre': 'Juan Perez'}
    cursor.lastrowid = 1

    # Mockear os.path.join para que guarde en tmp_path
    mocker.patch('paginaInicio.paginaInicio.os.makedirs')
    mocker.patch('paginaInicio.paginaInicio.os.path.join', return_value=str(tmp_path / 'archivo.jpg'))

    archivo_falso = (BytesIO(b'contenido'), 'ine.jpg')

    respuesta = cliente_flask.post(
        '/digitalizarDocumentos/subir',
        data={
            'tipoDocumento': 'ine',
            'id_persona': '1',
            'tipo_persona': 'jugador',
            'archivo': archivo_falso
        },
        content_type='multipart/form-data'
    )

    assert respuesta.status_code == 200
    assert respuesta.get_json()['ok'] is True


def test_subir_documento_error_bd(cliente_flask, mock_mysql):
    """POST con error de BD en el INSERT debe propagar la excepción (TESTING=True)."""
    from io import BytesIO
    import pytest
    mysql_mock, cursor = mock_mysql

    cursor.fetchone.return_value = {'nombre': 'Juan Perez'}

    def execute_con_fallo(sql, *args, **kwargs):
        if 'INSERT' in sql.upper():
            raise Exception("Error de BD")
        return None

    cursor.execute.side_effect = execute_con_fallo

    archivo_falso = (BytesIO(b'contenido'), 'ine.jpg')

    # En modo TESTING, Flask propaga la excepción en lugar de devolver 500
    with pytest.raises(Exception, match="Error de BD"):
        cliente_flask.post(
            '/digitalizarDocumentos/subir',
            data={
                'tipoDocumento': 'ine',
                'id_persona': '1',
                'archivo': archivo_falso
            },
            content_type='multipart/form-data'
        )

# ══════════════════════════════════════════════════
# PRUEBAS PARA eliminar_documento()
# ══════════════════════════════════════════════════

def test_eliminar_documento_exitoso(cliente_flask, mock_mysql, mock_notificar, mocker):
    """POST /digitalizarDocumentos/eliminar/1 debe eliminar el documento."""
    mysql_mock, cursor = mock_mysql
    cursor.fetchone.return_value = {'ruta': 'static/uploads/archivo.jpg'}
    mocker.patch('paginaInicio.paginaInicio.os.path.exists', return_value=False)

    respuesta = cliente_flask.post('/digitalizarDocumentos/eliminar/1')

    assert respuesta.status_code == 200
    assert respuesta.get_json()['ok'] is True


def test_eliminar_documento_no_existe(cliente_flask, mock_mysql):
    """POST /digitalizarDocumentos/eliminar/999 debe devolver 404."""
    mysql_mock, cursor = mock_mysql
    cursor.fetchone.return_value = None

    respuesta = cliente_flask.post('/digitalizarDocumentos/eliminar/999')

    assert respuesta.status_code == 404
    assert respuesta.get_json()['ok'] is False


# ══════════════════════════════════════════════════
# PRUEBAS PARA expedientes()
# ══════════════════════════════════════════════════

def test_expedientes_renderiza(cliente_flask, mocker):
    """GET /expedientes debe renderizar la plantilla."""
    mocker.patch('paginaInicio.paginaInicio.render_template', return_value='OK')

    respuesta = cliente_flask.get('/expedientes')

    assert respuesta.status_code == 200


# ══════════════════════════════════════════════════
# PRUEBAS PARA buscar_expediente()
# ══════════════════════════════════════════════════

def test_buscar_expediente_sin_termino(cliente_flask, mock_mysql):
    """GET /expedientes/buscar sin término debe devolver 400."""
    respuesta = cliente_flask.get('/expedientes/buscar')

    assert respuesta.status_code == 400
    assert respuesta.get_json()['ok'] is False


def test_buscar_expediente_con_resultados(cliente_flask, mock_mysql):
    """GET /expedientes/buscar?termino=Juan debe devolver solo 1 resultado."""
    mysql_mock, cursor = mock_mysql

    # La ruta hace 3 fetchall(): jugadores, entrenadores, árbitros.
    # Solo el primero devuelve resultado; los otros van vacíos.
    cursor.fetchall.side_effect = [
        [   # 1) jugadores → 1 resultado
            {
                'id_expediente': 1,
                'estatus': 'activo',
                'fecha_creacion': None,
                'id_persona': 1,
                'nombre_completo': 'Juan Perez',
                'numero_registro': 'JUG-001',
                'categoria': 'JUVENIL',
                'tipo': 'jugador'
            }
        ],
        [],  # 2) entrenadores → 0
        []   # 3) árbitros → 0
    ]

    respuesta = cliente_flask.get('/expedientes/buscar?termino=Juan')

    assert respuesta.status_code == 200
    data = respuesta.get_json()
    assert data['ok'] is True
    assert len(data['resultados']) == 1
    assert data['resultados'][0]['nombre'] == 'Juan Perez'

def test_buscar_expediente_sin_resultados(cliente_flask, mock_mysql):
    """GET /expedientes/buscar?termino=XYZ debe devolver 404."""
    mysql_mock, cursor = mock_mysql
    cursor.fetchall.return_value = []

    respuesta = cliente_flask.get('/expedientes/buscar?termino=XYZ')

    assert respuesta.status_code == 404
    assert respuesta.get_json()['ok'] is False


# ══════════════════════════════════════════════════
# PRUEBAS PARA generar_expediente()
# ══════════════════════════════════════════════════

def test_generar_expediente_sin_id(cliente_flask, mock_mysql):
    """POST /expedientes/generar sin id_persona debe devolver 400."""
    respuesta = cliente_flask.post(
        '/expedientes/generar',
        json={'tipo': 'jugador'}
    )

    assert respuesta.status_code == 400
    assert respuesta.get_json()['ok'] is False


def test_generar_expediente_tipo_invalido(cliente_flask, mock_mysql):
    """POST con tipo inválido debe devolver 400."""
    respuesta = cliente_flask.post(
        '/expedientes/generar',
        json={'id_persona': 1, 'tipo': 'invalido'}
    )

    assert respuesta.status_code == 400
    assert respuesta.get_json()['ok'] is False


def test_generar_expediente_sin_datos(cliente_flask, mock_mysql):
    """POST con id_persona inexistente debe devolver 404."""
    mysql_mock, cursor = mock_mysql
    cursor.fetchone.return_value = None

    respuesta = cliente_flask.post(
        '/expedientes/generar',
        json={'id_persona': 999, 'tipo': 'jugador'}
    )

    assert respuesta.status_code == 404
    assert respuesta.get_json()['ok'] is False


# ══════════════════════════════════════════════════
# PRUEBAS PARA _formatear_tamano()
# ══════════════════════════════════════════════════

def test_formatear_tamano_bytes():
    """_formatear_tamano(500) debe devolver '500.0 Bytes'."""
    from paginaInicio.paginaInicio import _formatear_tamano
    resultado = _formatear_tamano(500)
    assert 'Bytes' in resultado


def test_formatear_tamano_kb():
    """_formatear_tamano(2048) debe devolver '2.0 KB'."""
    from paginaInicio.paginaInicio import _formatear_tamano
    resultado = _formatear_tamano(2048)
    assert 'KB' in resultado


def test_formatear_tamano_cero():
    """_formatear_tamano(0) debe devolver '0 Bytes'."""
    from paginaInicio.paginaInicio import _formatear_tamano
    resultado = _formatear_tamano(0)
    assert resultado == '0 Bytes'