# test/test_reportes.py
import pytest
from io import BytesIO


# ══════════════════════════════════════════════════
# REPORTE GENERAL
# ══════════════════════════════════════════════════

def test_reporte_general_renderiza(cliente_flask, mock_mysql, mocker):
    """GET /reportes/ debe renderizar la plantilla con los contadores."""
    mysql_mock, cursor = mock_mysql

    # La ruta hace 4 fetchone() en orden:
    # jugador, liga, equipo, pago completado
    cursor.fetchone.side_effect = [
        {'t': 100},  # total_jugadores
        {'t': 5},    # total_ligas
        {'t': 20},   # total_equipos
        {'t': 50},   # pagos_completados
    ]

    # Mockeamos render_template para no depender de la plantilla real
    mocker.patch('reportes.reportes.render_template', return_value='OK')

    respuesta = cliente_flask.get('/reportes/')

    assert respuesta.status_code == 200


# ══════════════════════════════════════════════════
# REPORTE INGRESOS
# ══════════════════════════════════════════════════

def test_reporte_ingresos_sin_filtros(cliente_flask, mock_mysql, mocker):
    """GET /reportes/ingresos sin filtros debe renderizar con todos los pagos."""
    mysql_mock, cursor = mock_mysql

    # fetchall: lista de pagos
    cursor.fetchall.return_value = [
        {
            'id_pago': 1,
            'fecha_pago': None,
            'estatus': 'Completado',
            'metodo_pago': 'EFECTIVO',
            'referencia': 'REF-001',
            'nombre_jugador': 'Juan Perez',
            'numero_registro': 'JUG-001'
        }
    ]

    # fetchone: 3 contadores (completados, pendientes, cancelados)
    cursor.fetchone.side_effect = [
        {'t': 50},  # completados
        {'t': 10},  # pendientes
        {'t': 3},   # cancelados
    ]

    mocker.patch('reportes.reportes.render_template', return_value='OK')

    respuesta = cliente_flask.get('/reportes/ingresos')

    assert respuesta.status_code == 200


def test_reporte_ingresos_con_filtros(cliente_flask, mock_mysql, mocker):
    """GET con fecha_desde, fecha_hasta y estatus debe aplicar filtros."""
    mysql_mock, cursor = mock_mysql

    cursor.fetchall.return_value = []
    cursor.fetchone.side_effect = [
        {'t': 0}, {'t': 0}, {'t': 0}
    ]

    mocker.patch('reportes.reportes.render_template', return_value='OK')

    respuesta = cliente_flask.get(
        '/reportes/ingresos?fecha_desde=2026-01-01&fecha_hasta=2026-04-01&estatus=Completado'
    )

    assert respuesta.status_code == 200
    # Verificamos que se construyó el WHERE con los 3 filtros
    # (buscando en las llamadas a execute)
    llamadas = [str(call) for call in cursor.execute.call_args_list]
    assert any('fecha_pago >= %s' in l for l in llamadas)
    assert any('fecha_pago <= %s' in l for l in llamadas)
    assert any('estatus = %s' in l for l in llamadas)


def test_reporte_ingresos_solo_estatus(cliente_flask, mock_mysql, mocker):
    """GET con solo estatus debe aplicar solo ese filtro."""
    mysql_mock, cursor = mock_mysql

    cursor.fetchall.return_value = []
    cursor.fetchone.side_effect = [
        {'t': 0}, {'t': 0}, {'t': 0}
    ]

    mocker.patch('reportes.reportes.render_template', return_value='OK')

    respuesta = cliente_flask.get('/reportes/ingresos?estatus=Pendiente')

    assert respuesta.status_code == 200
    llamadas = [str(call) for call in cursor.execute.call_args_list]
    assert any('estatus = %s' in l for l in llamadas)
    # No debe haber filtros de fecha
    assert not any('fecha_pago >=' in l for l in llamadas)
    assert not any('fecha_pago <=' in l for l in llamadas)


# ══════════════════════════════════════════════════
# REPORTE INSCRIPCIÓN
# ══════════════════════════════════════════════════

def test_reporte_inscripcion_renderiza(cliente_flask, mock_mysql, mocker):
    """GET /reportes/inscripcion debe renderizar con jugadores y contadores."""
    mysql_mock, cursor = mock_mysql

    cursor.fetchall.return_value = [
        {
            'id_jugador': 1,
            'nombre': 'Juan Perez',
            'curp': 'PEPJ000101HDFRRN01',
            'correo_electronico': 'juan@test.com',
            'estatus_expediente': 'activo',
            'fecha_creacion': None
        }
    ]

    # 3 fetchone(): total jugadores, activos, nuevos_mes
    cursor.fetchone.side_effect = [
        {'t': 100},  # total
        {'t': 80},   # activos
        {'t': 5},    # nuevos_mes
    ]

    mocker.patch('reportes.reportes.render_template', return_value='OK')

    respuesta = cliente_flask.get('/reportes/inscripcion')

    assert respuesta.status_code == 200


# ══════════════════════════════════════════════════
# REPORTE SISTEMA
# ══════════════════════════════════════════════════

def test_reporte_sistema_renderiza(cliente_flask, mock_mysql, mocker):
    """GET /reportes/sistema debe renderizar con todos los contadores."""
    mysql_mock, cursor = mock_mysql

    # 11 fetchone() en orden:
    # usuarios, ligas, equipos, jugadores, afiliaciones,
    # pagos ok, pagos pend, pagos cancel,
    # solicitudes pend, autorizados hoy, total docs
    cursor.fetchone.side_effect = [
        {'t': 10},   # total_usuarios
        {'t': 5},    # total_ligas
        {'t': 20},   # total_equipos
        {'t': 100},  # total_jugadores
        {'t': 90},   # total_afiliaciones
        {'t': 50},   # pagos_ok
        {'t': 10},   # pagos_pend
        {'t': 3},    # pagos_cancel
        {'t': 7},    # solicitudes_pend
        {'t': 2},    # autorizados_hoy
        {'t': 30},   # total_docs
    ]

    # 2 fetchall(): ligas con equipos/jugadores, usuarios por rol
    cursor.fetchall.side_effect = [
        [   # ligas
            {
                'nombre_liga': 'LIGA PREMIER',
                'categoria': 'VARONIL',
                'equipos': 5,
                'jugadores': 50
            }
        ],
        [   # usuarios por rol
            {'rol': 'Presidente', 'total': 1},
            {'rol': 'Entrenador', 'total': 9},
        ]
    ]

    mocker.patch('reportes.reportes.render_template', return_value='OK')

    respuesta = cliente_flask.get('/reportes/sistema')

    assert respuesta.status_code == 200


# ══════════════════════════════════════════════════
# EXPORTAR EXCEL
# ══════════════════════════════════════════════════

def test_exportar_ingresos_excel(cliente_flask, mock_mysql):
    """GET /reportes/ingresos/excel debe devolver un archivo Excel."""
    mysql_mock, cursor = mock_mysql

    cursor.fetchall.return_value = [
        {
            'id_pago': 1,
            'fecha_pago': None,
            'estatus': 'Completado',
            'metodo_pago': 'EFECTIVO',
            'referencia': 'REF-001',
            'nombre_jugador': 'Juan Perez',
            'numero_registro': 'JUG-001'
        }
    ]

    respuesta = cliente_flask.get('/reportes/ingresos/excel')

    assert respuesta.status_code == 200
    # El content-type debe ser el de Excel
    assert 'spreadsheet' in respuesta.content_type or 'excel' in respuesta.content_type


def test_exportar_inscripcion_excel(cliente_flask, mock_mysql):
    """GET /reportes/inscripcion/excel debe devolver un archivo Excel."""
    mysql_mock, cursor = mock_mysql

    cursor.fetchall.return_value = [
        {
            'id_jugador': 1,
            'nombre': 'Juan Perez',
            'curp': 'PEPJ000101HDFRRN01',
            'correo_electronico': 'juan@test.com',
            'estatus_expediente': 'activo',
            'fecha_creacion': None
        }
    ]

    respuesta = cliente_flask.get('/reportes/inscripcion/excel')

    assert respuesta.status_code == 200
    assert 'spreadsheet' in respuesta.content_type or 'excel' in respuesta.content_type