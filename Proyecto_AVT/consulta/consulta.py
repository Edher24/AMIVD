# Adriana Nicole Guzman Ahuatzi
#01/04/2026
# Rutas para consultas generales: registros, afiliados, ligas, pagos, tutores
from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for
from extensiones import mysql

consulta = Blueprint('consulta', __name__, url_prefix="/consulta")


def login_requerido(f):
    from functools import wraps
    @wraps(f)
    def decorador(*args, **kwargs):
        if 'id_usuario' not in session:
            return redirect(url_for('auth.iniciarSesion'))
        return f(*args, **kwargs)
    return decorador


# ══════════════════════════════════════════════════
# GENERAL
# ══════════════════════════════════════════════════

@consulta.route("/")
@login_requerido
def consultaGeneral():
    return render_template("consulta/consultaGeneral.html")


# ══════════════════════════════════════════════════
# REGISTROS — todos (jugador + entrenador + árbitro)
# ══════════════════════════════════════════════════

@consulta.route("/registro")
@login_requerido
def consultarRegistro():
    nombre = request.args.get('nombre', '').strip()
    curp   = request.args.get('curp',   '').strip()
    rol    = request.args.get('rol',    '').strip()

    cur = mysql.connection.cursor()
    resultados = []

    tablas = {
        'jugador':    ('jugador',    'id_jugador'),
        'entrenador': ('entrenador', 'id_entrenador'),
        'arbitro':    ('arbitro',    'id_arbitro'),
    }

    tipos_buscar = [rol] if rol in tablas else list(tablas.keys())

    for tipo in tipos_buscar:
        tabla, pk = tablas[tipo]
        condiciones = []
        valores     = []

        if nombre:
            condiciones.append(
                "CONCAT(apellido_paterno,' ',apellido_materno,' ',nombres) LIKE %s")
            valores.append(f'%{nombre}%')
        if curp:
            condiciones.append("curp LIKE %s")
            valores.append(f'%{curp}%')

        where = f"WHERE {' AND '.join(condiciones)}" if condiciones else ""

        # Intentar leer categoria de la tabla; si no existe (BD sin migrar), usar NULL
        if tipo == 'jugador':
            col_categoria = 'categoria'   # existe tras ejecutar agregar_categoria_jugador.sql
            col_fecha_reg = 'NULL AS fecha_registro'
        else:
            col_categoria = 'categoria'
            col_fecha_reg = 'fecha_registro'

        try:
            cur.execute(f"""
                SELECT {pk} AS id,
                       apellido_paterno, apellido_materno, nombres,
                       curp, {col_categoria}, {col_fecha_reg},
                       '{tipo}' AS tipo
                FROM {tabla}
                {where}
            """, valores)
        except Exception:
            # Fallback: columna categoria no existe aún en esta tabla
            cur.execute(f"""
                SELECT {pk} AS id,
                       apellido_paterno, apellido_materno, nombres,
                       curp, NULL AS categoria, NULL AS fecha_registro,
                       '{tipo}' AS tipo
                FROM {tabla}
                {where}
            """, valores)
        resultados += cur.fetchall()

    # Contadores totales
    cur.execute("SELECT COUNT(*) AS total FROM jugador")
    total_j = cur.fetchone()['total']
    cur.execute("SELECT COUNT(*) AS total FROM entrenador")
    total_e = cur.fetchone()['total']
    cur.execute("SELECT COUNT(*) AS total FROM arbitro")
    total_a = cur.fetchone()['total']
    cur.close()

    return render_template(
        "consulta/consultarRegistro.html",
        resultados=resultados,
        total_jugadores=total_j,
        total_entrenadores=total_e,
        total_arbitros=total_a,
        filtro_nombre=nombre,
        filtro_curp=curp,
        filtro_rol=rol
    )


# ══════════════════════════════════════════════════
# AFILIADOS — con filtro de estatus
# ══════════════════════════════════════════════════

@consulta.route("/afiliado")
@login_requerido
def consultarAfiliado():
    nombre  = request.args.get('nombre',  '').strip()
    curp    = request.args.get('curp',    '').strip()
    estatus = request.args.get('estatus', 'activo').strip()  # NUEVO

    cur = mysql.connection.cursor()
    condiciones = []
    valores     = []

    if nombre:
        condiciones.append(
            "CONCAT(j.apellido_paterno,' ',j.apellido_materno,' ',j.nombres) LIKE %s")
        valores.append(f'%{nombre}%')
    if curp:
        condiciones.append("j.curp LIKE %s")
        valores.append(f'%{curp}%')

    # NUEVO: filtro por estatus
    if estatus == 'todos':
        condiciones.append("e.estatus IN ('activo', 'inactivo', 'cerrado')")
    else:
        condiciones.append("e.estatus = %s")
        valores.append(estatus)

    where = f"WHERE {' AND '.join(condiciones)}" if condiciones else ""

    try:
        cur.execute(f"""
            SELECT j.id_jugador AS id,
                   j.apellido_paterno, j.apellido_materno, j.nombres,
                   j.curp, j.categoria,
                   e.id_expediente, e.estatus, 'jugador' AS tipo
            FROM jugador j
            JOIN expediente e ON e.id_jugador = j.id_jugador
            {where}
            ORDER BY j.apellido_paterno
        """, valores)
    except Exception:
        cur.execute(f"""
            SELECT j.id_jugador AS id,
                   j.apellido_paterno, j.apellido_materno, j.nombres,
                   j.curp, NULL AS categoria,
                   e.id_expediente, e.estatus, 'jugador' AS tipo
            FROM jugador j
            JOIN expediente e ON e.id_jugador = j.id_jugador
            {where}
            ORDER BY j.apellido_paterno
        """, valores)
    resultados = cur.fetchall()

    # Contadores
    cur.execute("""
        SELECT COUNT(*) AS total FROM jugador j
        JOIN expediente e ON e.id_jugador = j.id_jugador
        WHERE e.estatus = 'activo'
    """)
    activos_j = cur.fetchone()['total']

    cur.execute("""
        SELECT COUNT(*) AS total FROM jugador j
        JOIN expediente e ON e.id_jugador = j.id_jugador
        WHERE e.estatus = 'inactivo'
    """)
    inactivos_j = cur.fetchone()['total']

    cur.close()

    return render_template(
        "consulta/consultarAfiliado.html",
        resultados=resultados,
        activos_jugadores=activos_j,
        inactivos_jugadores=inactivos_j,
        activos_entrenadores=0, activos_arbitros=0,
        filtro_nombre=nombre, filtro_curp=curp, filtro_estatus=estatus
    )


# ── Detalle de un afiliado (modal) ────────────────
@consulta.route("/afiliado/<int:id_jugador>")
@login_requerido
def detalleAfiliado(id_jugador):
    from extensiones import notificar
    cur = mysql.connection.cursor()

    try:
        cur.execute("""
            SELECT j.id_jugador, j.apellido_paterno, j.apellido_materno, j.nombres,
                   j.curp, j.fecha_nacimiento, j.celular, j.telefono,
                   j.correo_electronico, j.categoria,
                   e.id_expediente, e.estatus AS estatus_expediente
            FROM jugador j
            JOIN expediente e ON e.id_jugador = j.id_jugador
            WHERE j.id_jugador = %s
            LIMIT 1
        """, (id_jugador,))
    except Exception:
        cur.execute("""
            SELECT j.id_jugador, j.apellido_paterno, j.apellido_materno, j.nombres,
                   j.curp, j.fecha_nacimiento, j.celular, j.telefono,
                   j.correo_electronico, NULL AS categoria,
                   e.id_expediente, e.estatus AS estatus_expediente
            FROM jugador j
            JOIN expediente e ON e.id_jugador = j.id_jugador
            WHERE j.id_jugador = %s
            LIMIT 1
        """, (id_jugador,))
    jugador = cur.fetchone()

    if not jugador:
        cur.close()
        return jsonify({'ok': False, 'mensaje': 'Jugador no encontrado'}), 404

    # Sanciones activas
    try:
        cur.execute("""
            SELECT s.id_sancion, s.tipo_sancion, s.fecha_sancion,
                   s.fecha_fin_sancion, s.motivo, s.estatus,
                   l.nombre_liga
            FROM sanciones s
            LEFT JOIN liga l ON l.id_liga = s.id_liga
            WHERE s.id_jugador = %s
            ORDER BY s.fecha_sancion DESC
        """, (id_jugador,))
        sanciones = cur.fetchall()
    except Exception:
        sanciones = []

    # Ligas disponibles para nueva sanción
    cur.execute("SELECT id_liga, nombre_liga FROM liga ORDER BY nombre_liga")
    ligas = cur.fetchall()
    cur.close()

    def fmt(d):
        return d.strftime('%Y-%m-%d') if d else None

    data_jugador = {k: (fmt(v) if hasattr(v, 'strftime') else v)
                    for k, v in jugador.items()}
    data_sanciones = [
        {k: (fmt(v) if hasattr(v, 'strftime') else v) for k, v in s.items()}
        for s in sanciones
    ]

    return jsonify({
        'ok':       True,
        'jugador':  data_jugador,
        'sanciones': data_sanciones,
        'ligas':    ligas,
    })


# ── Cambiar categoría ─────────────────────────────
@consulta.route("/afiliado/<int:id_jugador>/categoria", methods=["POST"])
@login_requerido
def cambiarCategoria(id_jugador):
    from extensiones import notificar
    nueva = request.json.get('categoria', '').strip().upper()
    if not nueva:
        return jsonify({'ok': False, 'mensaje': 'Categoría requerida'}), 400
    cur = mysql.connection.cursor()
    try:
        cur.execute("UPDATE jugador SET categoria = %s WHERE id_jugador = %s",
                    (nueva, id_jugador))
        mysql.connection.commit()
        notificar(cur, session['id_usuario'],
                  f"Categoría del jugador #{id_jugador} actualizada a '{nueva}'.")
        mysql.connection.commit()
        cur.close()
        return jsonify({'ok': True, 'mensaje': f'Categoría actualizada a {nueva}.'})
    except Exception as e:
        mysql.connection.rollback()
        cur.close()
        return jsonify({'ok': False, 'mensaje': str(e)}), 500


# ── Cambiar estatus del expediente (activo/inactivo) ──
@consulta.route("/afiliado/<int:id_jugador>/estatus", methods=["POST"])
@login_requerido
def cambiarEstatusAfiliado(id_jugador):
    from extensiones import notificar
    nuevo = request.json.get('estatus', '').strip().lower()
    if nuevo not in ('activo', 'inactivo', 'cerrado'):
        return jsonify({'ok': False, 'mensaje': 'Estatus inválido'}), 400
    cur = mysql.connection.cursor()
    try:
        cur.execute("""
            UPDATE expediente SET estatus = %s
            WHERE id_jugador = %s
        """, (nuevo, id_jugador))
        mysql.connection.commit()
        notificar(cur, session['id_usuario'],
                  f"Expediente del jugador #{id_jugador} marcado como '{nuevo}'.")
        mysql.connection.commit()
        cur.close()
        return jsonify({'ok': True, 'mensaje': f'Estatus actualizado a {nuevo}.'})
    except Exception as e:
        mysql.connection.rollback()
        cur.close()
        return jsonify({'ok': False, 'mensaje': str(e)}), 500


# ── Agregar sanción ───────────────────────────────
@consulta.route("/afiliado/<int:id_jugador>/sancion", methods=["POST"])
@login_requerido
def agregarSancion(id_jugador):
    from extensiones import notificar
    d = request.json or {}
    tipo_sancion    = d.get('tipo_sancion', '').strip()
    id_liga         = d.get('id_liga')
    motivo          = d.get('motivo', '').strip()
    fecha_fin       = d.get('fecha_fin_sancion') or None

    if not tipo_sancion or not motivo or not id_liga:
        return jsonify({'ok': False, 'mensaje': 'Tipo, liga y motivo son obligatorios'}), 400

    cur = mysql.connection.cursor()
    try:
        cur.execute("""
            INSERT INTO sanciones
                (id_jugador, id_liga, tipo_sancion, fecha_sancion,
                 fecha_fin_sancion, motivo, estatus)
            VALUES (%s, %s, %s, CURDATE(), %s, %s, 'Activa')
        """, (id_jugador, id_liga, tipo_sancion, fecha_fin, motivo))
        mysql.connection.commit()
        nuevo_id = cur.lastrowid
        notificar(cur, session['id_usuario'],
                  f"Sanción '{tipo_sancion}' registrada para jugador #{id_jugador}.")
        mysql.connection.commit()
        cur.close()
        return jsonify({'ok': True, 'mensaje': 'Sanción registrada.', 'id': nuevo_id})
    except Exception as e:
        mysql.connection.rollback()
        cur.close()
        return jsonify({'ok': False, 'mensaje': str(e)}), 500


# ══════════════════════════════════════════════════
# LIGAS
# ══════════════════════════════════════════════════

@consulta.route("/ligas")
@login_requerido
def consultarLigas():
    nombre = request.args.get('nombre', '').strip()
    filtro_estado = request.args.get('estado', '').strip()

    cur = mysql.connection.cursor()
    condiciones = []
    valores     = []
    if nombre:
        condiciones.append("l.nombre_liga LIKE %s")
        valores.append(f'%{nombre}%')

    tiene_estado = False
    try:
        cur.execute("SELECT estado FROM liga LIMIT 1")
        cur.fetchone()
        tiene_estado = True
    except Exception:
        pass

    if filtro_estado and tiene_estado:
        condiciones.append("l.estado = %s")
        valores.append(filtro_estado)

    where = f"WHERE {' AND '.join(condiciones)}" if condiciones else ""

    col_estado = "COALESCE(l.estado, 'activo') AS estado" if tiene_estado else "'activo' AS estado"

    cur.execute(f"""
        SELECT l.id_liga, l.nombre_liga, l.categoria,
               {col_estado},
               COUNT(DISTINCT e.id_equipo)   AS total_equipos,
               COUNT(DISTINCT jl.id_jugador) AS total_jugadores
        FROM liga l
        LEFT JOIN equipo e        ON e.id_liga  = l.id_liga
        LEFT JOIN jugador_liga jl ON jl.id_liga = l.id_liga
        {where}
        GROUP BY l.id_liga
        ORDER BY l.nombre_liga
    """, valores)
    ligas = cur.fetchall()

    if tiene_estado:
        cur.execute("SELECT COUNT(*) AS t FROM liga WHERE estado = 'activo'")
        activas = cur.fetchone()['t']
        cur.execute("SELECT COUNT(*) AS t FROM liga WHERE estado = 'inactivo'")
        inactivas = cur.fetchone()['t']
    else:
        cur.execute("SELECT COUNT(*) AS t FROM liga")
        activas = cur.fetchone()['t']
        inactivas = 0

    cur.execute("SELECT COUNT(*) AS t FROM equipo")
    total_equipos = cur.fetchone()['t']
    cur.execute("SELECT COUNT(*) AS t FROM jugador")
    total_jugadores = cur.fetchone()['t']
    cur.close()

    return render_template(
        "consulta/consultarLigas.html",
        ligas=ligas,
        activas=activas,
        inactivas=inactivas,
        total_equipos=total_equipos,
        total_jugadores=total_jugadores,
        filtro_nombre=nombre,
        filtro_estado=filtro_estado,
    )


@consulta.route("/ligas/toggle/<int:id_liga>", methods=["POST"])
@login_requerido
def toggleEstadoLiga(id_liga):
    from extensiones import notificar
    cur = mysql.connection.cursor()
    try:
        cur.execute("SELECT estado FROM liga WHERE id_liga = %s", (id_liga,))
        fila = cur.fetchone()
        if not fila:
            cur.close()
            return jsonify({'ok': False, 'mensaje': 'Liga no encontrada'}), 404

        nuevo = 'inactivo' if fila['estado'] == 'activo' else 'activo'
        cur.execute("UPDATE liga SET estado = %s WHERE id_liga = %s", (nuevo, id_liga))
        mysql.connection.commit()
        notificar(cur, session['id_usuario'],
                  f"Liga #{id_liga} marcada como '{nuevo}'.")
        mysql.connection.commit()
        cur.close()
        return jsonify({'ok': True, 'nuevo_estado': nuevo,
                        'mensaje': f'Liga marcada como {nuevo}.'})
    except Exception as e:
        mysql.connection.rollback()
        cur.close()
        return jsonify({'ok': False,
                        'mensaje': 'Ejecuta agregar_estado_liga.sql en Workbench primero.'}), 500


# ══════════════════════════════════════════════════
# EQUIPOS
# ══════════════════════════════════════════════════

@consulta.route("/equipo")
@login_requerido
def consultarEquipo():
    nombre    = request.args.get('nombre',    '').strip()
    id_liga   = request.args.get('id_liga',   '').strip()
    categoria = request.args.get('categoria', '').strip()

    cur = mysql.connection.cursor()
    condiciones = []
    valores     = []

    if nombre:
        condiciones.append("e.nombre_equipo LIKE %s")
        valores.append(f'%{nombre}%')
    if id_liga:
        condiciones.append("e.id_liga = %s")
        valores.append(id_liga)
    if categoria:
        condiciones.append("e.categoria = %s")
        valores.append(categoria)

    where = f"WHERE {' AND '.join(condiciones)}" if condiciones else ""

    try:
        cur.execute(f"""
            SELECT e.id_equipo, e.nombre_equipo, e.categoria, e.estado,
                   l.id_liga, l.nombre_liga
            FROM equipo e
            JOIN liga l ON l.id_liga = e.id_liga
            {where}
            ORDER BY l.nombre_liga, e.nombre_equipo
        """, valores)
    except Exception:
        cur.execute(f"""
            SELECT e.id_equipo, e.nombre_equipo, e.categoria, 'activo' AS estado,
                   l.id_liga, l.nombre_liga
            FROM equipo e
            JOIN liga l ON l.id_liga = e.id_liga
            {where}
            ORDER BY l.nombre_liga, e.nombre_equipo
        """, valores)
    equipos = cur.fetchall()

    cur.execute("SELECT COUNT(*) AS t FROM equipo")
    total_equipos = cur.fetchone()['t']
    cur.execute("SELECT id_liga, nombre_liga FROM liga ORDER BY nombre_liga")
    ligas = cur.fetchall()
    cur.close()

    return render_template(
        "consulta/consultarEquipo.html",
        equipos=equipos,
        total_equipos=total_equipos,
        ligas=ligas,
        filtro_nombre=nombre,
        filtro_liga=id_liga,
        filtro_categoria=categoria,
    )


@consulta.route("/equipo/<int:id_equipo>")
@login_requerido
def detalleEquipo(id_equipo):
    cur = mysql.connection.cursor()

    try:
        cur.execute("""
            SELECT e.id_equipo, e.nombre_equipo, e.categoria, e.estado,
                   l.id_liga, l.nombre_liga
            FROM equipo e
            JOIN liga l ON l.id_liga = e.id_liga
            WHERE e.id_equipo = %s
        """, (id_equipo,))
    except Exception:
        cur.execute("""
            SELECT e.id_equipo, e.nombre_equipo, e.categoria, 'activo' AS estado,
                   l.id_liga, l.nombre_liga
            FROM equipo e
            JOIN liga l ON l.id_liga = e.id_liga
            WHERE e.id_equipo = %s
        """, (id_equipo,))
    equipo = cur.fetchone()

    if not equipo:
        cur.close()
        return jsonify({'ok': False, 'mensaje': 'Equipo no encontrado'}), 404

    jugadores = []
    try:
        cur.execute("""
            SELECT id_jugador,
                   CONCAT(apellido_paterno,' ',apellido_materno,' ',nombres) AS nombre,
                   curp, categoria
            FROM jugador
            WHERE id_equipo = %s
            ORDER BY apellido_paterno
        """, (id_equipo,))
        jugadores = cur.fetchall()
    except Exception:
        pass

    cur.close()
    return jsonify({
        'ok':       True,
        'equipo':   equipo,
        'jugadores': jugadores,
    })


@consulta.route("/equipo/<int:id_equipo>/categoria", methods=["POST"])
@login_requerido
def cambiarCategoriaEquipo(id_equipo):
    from extensiones import notificar
    nueva = request.json.get('categoria', '').strip().upper()
    if not nueva:
        return jsonify({'ok': False, 'mensaje': 'Categoría requerida'}), 400
    cur = mysql.connection.cursor()
    try:
        cur.execute("UPDATE equipo SET categoria = %s WHERE id_equipo = %s",
                    (nueva, id_equipo))
        mysql.connection.commit()
        notificar(cur, session['id_usuario'],
                  f"Categoría del equipo #{id_equipo} actualizada a '{nueva}'.")
        mysql.connection.commit()
        cur.close()
        return jsonify({'ok': True, 'mensaje': f'Categoría actualizada a {nueva}.'})
    except Exception as e:
        mysql.connection.rollback()
        cur.close()
        return jsonify({'ok': False, 'mensaje': str(e)}), 500


@consulta.route("/equipo/<int:id_equipo>/estado", methods=["POST"])
@login_requerido
def toggleEstadoEquipo(id_equipo):
    from extensiones import notificar
    cur = mysql.connection.cursor()
    try:
        cur.execute("SELECT estado FROM equipo WHERE id_equipo = %s", (id_equipo,))
        fila = cur.fetchone()
        if not fila:
            cur.close()
            return jsonify({'ok': False, 'mensaje': 'Equipo no encontrado'}), 404

        nuevo = 'inactivo' if fila['estado'] == 'activo' else 'activo'
        cur.execute("UPDATE equipo SET estado = %s WHERE id_equipo = %s", (nuevo, id_equipo))
        mysql.connection.commit()
        notificar(cur, session['id_usuario'],
                  f"Equipo #{id_equipo} marcado como '{nuevo}'.")
        mysql.connection.commit()
        cur.close()
        return jsonify({'ok': True, 'nuevo_estado': nuevo,
                        'mensaje': f'Equipo marcado como {nuevo}.'})
    except Exception as e:
        mysql.connection.rollback()
        cur.close()
        return jsonify({'ok': False,
                        'mensaje': 'Ejecuta agregar_estado_equipo.sql en Workbench primero.'}), 500


# ══════════════════════════════════════════════════
# PAGOS
# ══════════════════════════════════════════════════

@consulta.route("/pagos")
@login_requerido
def consultarPagos():
    nombre      = request.args.get('nombre',      '').strip()
    estatus     = request.args.get('estatus',     '').strip()
    fecha_desde = request.args.get('fecha_desde', '').strip()
    fecha_hasta = request.args.get('fecha_hasta', '').strip()

    cur = mysql.connection.cursor()
    condiciones = []
    valores     = []

    if nombre:
        condiciones.append("""
            CONCAT(j.apellido_paterno,' ',j.apellido_materno,' ',j.nombres) LIKE %s
        """)
        valores.append(f'%{nombre}%')
    if estatus:
        condiciones.append("p.estatus = %s")
        valores.append(estatus)
    if fecha_desde:
        condiciones.append("p.fecha_pago >= %s")
        valores.append(fecha_desde)
    if fecha_hasta:
        condiciones.append("p.fecha_pago <= %s")
        valores.append(fecha_hasta)

    where = f"WHERE {' AND '.join(condiciones)}" if condiciones else ""

    cur.execute(f"""
        SELECT p.id_pago, p.fecha_pago, p.estatus,
               p.metodo_pago, p.referencia,
               CONCAT(j.apellido_paterno,' ',j.apellido_materno,' ',j.nombres) AS nombre_persona,
               a.numero_registro
        FROM pago p
        JOIN afiliacion a ON a.id_afiliacion = p.id_afiliacion
        JOIN jugador j    ON j.id_jugador    = a.id_jugador
        {where}
        ORDER BY p.fecha_pago DESC
    """, valores)
    pagos = cur.fetchall()

    cur.execute("SELECT COUNT(*) AS t FROM pago WHERE estatus='Completado'")
    completados = cur.fetchone()['t']
    cur.execute("SELECT COUNT(*) AS t FROM pago WHERE estatus='Pendiente'")
    pendientes = cur.fetchone()['t']
    cur.execute("SELECT COUNT(*) AS t FROM pago WHERE estatus='Cancelado'")
    cancelados = cur.fetchone()['t']
    cur.close()

    return render_template(
        "consulta/consultarPagos.html",
        pagos=pagos,
        completados=completados,
        pendientes=pendientes,
        cancelados=cancelados,
        filtro_nombre=nombre,
        filtro_estatus=estatus,
        filtro_desde=fecha_desde,
        filtro_hasta=fecha_hasta
    )


# ══════════════════════════════════════════════════
# TUTORES
# ══════════════════════════════════════════════════

@consulta.route("/tutor")
@login_requerido
def consultarTutor():
    nombre_tutor = request.args.get('nombre_tutor', '').strip()
    nombre_menor = request.args.get('nombre_menor', '').strip()
    telefono     = request.args.get('telefono',     '').strip()

    cur = mysql.connection.cursor()

    condiciones = []
    valores     = []

    if nombre_tutor:
        condiciones.append("t.nombre_completo LIKE %s")
        valores.append(f'%{nombre_tutor}%')
    if nombre_menor:
        condiciones.append("""
            CONCAT(j.apellido_paterno,' ',j.apellido_materno,' ',j.nombres) LIKE %s
        """)
        valores.append(f'%{nombre_menor}%')
    if telefono:
        condiciones.append("t.celular LIKE %s")
        valores.append(f'%{telefono}%')

    where = f"WHERE {' AND '.join(condiciones)}" if condiciones else ""

    cur.execute(f"""
        SELECT t.id_tutor, t.nombre_completo, t.celular,
               t.correo_electronico, t.curp_tutor,
               CONCAT(j.apellido_paterno,' ',j.apellido_materno,' ',j.nombres) AS nombre_menor,
               TIMESTAMPDIFF(YEAR, j.fecha_nacimiento, CURDATE()) AS edad_menor,
               j.id_jugador
        FROM tutor_padre t
        JOIN jugador j ON j.id_jugador = t.id_jugador
        {where}
        ORDER BY t.nombre_completo
    """, valores)
    tutores_raw = cur.fetchall()

    tutores = {}
    for row in tutores_raw:
        tid = row['id_tutor']
        if tid not in tutores:
            tutores[tid] = {
                'id_tutor':           row['id_tutor'],
                'nombre_completo':    row['nombre_completo'],
                'celular':            row['celular'],
                'correo_electronico': row['correo_electronico'],
                'curp_tutor':         row['curp_tutor'],
                'menores':            []
            }
        tutores[tid]['menores'].append({
            'nombre': row['nombre_menor'],
            'edad':   row['edad_menor'],
            'id':     row['id_jugador']
        })

    cur.execute("SELECT COUNT(DISTINCT id_tutor) AS t FROM tutor_padre")
    total_tutores = cur.fetchone()['t']
    cur.execute("SELECT COUNT(DISTINCT id_jugador) AS t FROM tutor_padre")
    menores_con_tutor = cur.fetchone()['t']
    cur.execute("""
        SELECT COUNT(*) AS t FROM jugador
        WHERE id_jugador NOT IN (SELECT id_jugador FROM tutor_padre)
        AND TIMESTAMPDIFF(YEAR, fecha_nacimiento, CURDATE()) < 18
    """)
    sin_tutor = cur.fetchone()['t']
    cur.close()

    return render_template(
        "consulta/consultarTutor.html",
        tutores=list(tutores.values()),
        total_tutores=total_tutores,
        menores_con_tutor=menores_con_tutor,
        sin_tutor=sin_tutor,
        filtro_nombre_tutor=nombre_tutor,
        filtro_nombre_menor=nombre_menor,
        filtro_telefono=telefono
    )
# ══════════════════════════════════════════════════
# CONTADORES DE LIGAS (para actualización en tiempo real)
# ══════════════════════════════════════════════════

@consulta.route("/contadores-ligas")
@login_requerido
def contadores_ligas():
    cur = mysql.connection.cursor()
    
    tiene_estado = False
    try:
        cur.execute("SELECT estado FROM liga LIMIT 1")
        cur.fetchone()
        tiene_estado = True
    except Exception:
        pass
    
    if tiene_estado:
        cur.execute("SELECT COUNT(*) AS t FROM liga WHERE estado = 'activo'")
        activas = cur.fetchone()['t']
        cur.execute("SELECT COUNT(*) AS t FROM liga WHERE estado = 'inactivo'")
        inactivas = cur.fetchone()['t']
    else:
        cur.execute("SELECT COUNT(*) AS t FROM liga")
        activas = cur.fetchone()['t']
        inactivas = 0
    
    cur.execute("SELECT COUNT(*) AS t FROM equipo")
    total_equipos = cur.fetchone()['t']
    cur.execute("SELECT COUNT(*) AS t FROM jugador")
    total_jugadores = cur.fetchone()['t']
    cur.close()
    
    return jsonify({
        'activas': activas,
        'inactivas': inactivas,
        'total_equipos': total_equipos,
        'total_jugadores': total_jugadores
    })