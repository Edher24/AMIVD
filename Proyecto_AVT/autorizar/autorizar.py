# Adriana Nicole Guzman Ahuatzi
#01/04/2026
# Descripción: Rutas para la autorización de registros de jugadores, entrenadores, árbitros y registros externos.
from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for, flash
from extensiones import mysql, notificar

autorizar = Blueprint('autorizar', __name__, url_prefix="/autorizar")


def login_requerido(f):
    from functools import wraps
    @wraps(f)
    def decorador(*args, **kwargs):
        if 'id_usuario' not in session:
            return redirect(url_for('auth.iniciarSesion'))
        # RNF_06: solo Administrador y Presidente pueden autorizar
        if session.get('rol') not in ('Administrador', 'Presidente'):
            mensaje = 'No tienes los permisos suficientes'
            if request.method == 'GET' and not request.path.endswith('/contadores'):
                flash(mensaje, 'permiso')
                return redirect(url_for('registro.registroGeneral'))
            return jsonify({'ok': False, 'error': mensaje}), 403
        return f(*args, **kwargs)
    return decorador

# ══════════════════════════════════════════════════
# VISTA PRINCIPAL
# ══════════════════════════════════════════════════

@autorizar.route("/")
@login_requerido
def autorizarRegistro():
    cur = mysql.connection.cursor()

    # Contadores
    cur.execute("""
        SELECT
            SUM(estatus = 'Pendiente')  AS pendientes,
            SUM(estatus = 'Autorizado'
                AND DATE(fecha_solicitud) = CURDATE()) AS hoy,
            SUM(estatus = 'Rechazado')  AS rechazadas
        FROM autorizacion_pendiente
    """)
    contadores = cur.fetchone()

    # Solicitudes con datos de la persona relacionada
    cur.execute("""
        SELECT
            ap.id_autorizacion,
            ap.tipo_solicitud,
            ap.id_referencia,
            ap.fecha_solicitud,
            ap.estatus,
            ap.comentarios,
            COALESCE(
                CONCAT(j.apellido_paterno,' ',j.apellido_materno,' ',j.nombres),
                CONCAT(e.apellido_paterno,' ',e.apellido_materno,' ',e.nombres),
                CONCAT(a.apellido_paterno,' ',a.apellido_materno,' ',a.nombres),
                re.nombre_completo
            ) AS nombre_persona,
            COALESCE(j.curp, e.curp, a.curp, re.curp) AS curp,
            NULL AS categoria,
            COALESCE(j.correo_electronico, e.correo_electronico, a.correo_electronico, re.email) AS email_solicitante,
            COALESCE(
                CONCAT(j.apellido_paterno,' ',j.nombres),
                CONCAT(e.apellido_paterno,' ',e.nombres),
                CONCAT(a.apellido_paterno,' ',a.nombres),
                re.nombre_completo
            ) AS nombre_solicitante
        FROM autorizacion_pendiente ap
        LEFT JOIN jugador    j  ON j.id_jugador    = ap.id_referencia AND ap.tipo_solicitud = 'jugador'
        LEFT JOIN entrenador e  ON e.id_entrenador = ap.id_referencia AND ap.tipo_solicitud = 'entrenador'
        LEFT JOIN arbitro    a  ON a.id_arbitro    = ap.id_referencia AND ap.tipo_solicitud = 'arbitro'
        LEFT JOIN registro_externo re ON re.id_registro = ap.id_referencia
            AND j.id_jugador IS NULL AND e.id_entrenador IS NULL AND a.id_arbitro IS NULL
        ORDER BY
            FIELD(ap.estatus, 'Pendiente', 'Autorizado', 'Rechazado'),
            ap.fecha_solicitud DESC
    """)
    solicitudes = cur.fetchall()
    cur.close()

    return render_template(
        "autorizar/autorizarRegistro.html",
        solicitudes=solicitudes,
        contadores=contadores
    )


# ══════════════════════════════════════════════════
# CONTADORES (para actualizar en tiempo real)
# ══════════════════════════════════════════════════

@autorizar.route("/contadores")
@login_requerido
def contadores():
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT
            SUM(estatus = 'Pendiente')  AS pendientes,
            SUM(estatus = 'Autorizado'
                AND DATE(fecha_solicitud) = CURDATE()) AS hoy,
            SUM(estatus = 'Rechazado')  AS rechazadas
        FROM autorizacion_pendiente
    """)
    contadores = cur.fetchone()
    cur.close()
    return jsonify(contadores)


# ══════════════════════════════════════════════════
# APROBAR
# ══════════════════════════════════════════════════

@autorizar.route("/aprobar/<int:id_autorizacion>", methods=["POST"])
@login_requerido
def aprobar(id_autorizacion):
    cur = mysql.connection.cursor()
    try:
        cur.execute("""
            SELECT tipo_solicitud, id_referencia
            FROM autorizacion_pendiente
            WHERE id_autorizacion = %s
        """, (id_autorizacion,))
        sol = cur.fetchone()

        if not sol:
            cur.close()
            return jsonify({'ok': False, 'mensaje': 'Solicitud no encontrada'}), 404

        # Actualizar estatus
        cur.execute("""
            UPDATE autorizacion_pendiente
            SET estatus = 'Autorizado'
            WHERE id_autorizacion = %s
        """, (id_autorizacion,))

        notificar(cur, session['id_usuario'],
                  f"Registro de {sol['tipo_solicitud']} (ref: #{sol['id_referencia']}) autorizado correctamente.")

        mysql.connection.commit()
        cur.close()

        return jsonify({'ok': True, 'mensaje': 'Solicitud autorizada correctamente.'})

    except Exception as e:
        mysql.connection.rollback()
        cur.close()
        return jsonify({'ok': False, 'mensaje': str(e)}), 500


# ══════════════════════════════════════════════════
# RECHAZAR
# ══════════════════════════════════════════════════

@autorizar.route("/rechazar/<int:id_autorizacion>", methods=["POST"])
@login_requerido
def rechazar(id_autorizacion):
    comentario = request.form.get('comentario', '').strip()
    if not comentario:
        return jsonify({'ok': False, 'mensaje': 'El comentario es obligatorio'}), 400

    cur = mysql.connection.cursor()
    try:
        cur.execute("""
            SELECT tipo_solicitud, id_referencia
            FROM autorizacion_pendiente
            WHERE id_autorizacion = %s
        """, (id_autorizacion,))
        sol = cur.fetchone()

        if not sol:
            cur.close()
            return jsonify({'ok': False, 'mensaje': 'Solicitud no encontrada'}), 404

        cur.execute("""
            UPDATE autorizacion_pendiente
            SET estatus     = 'Rechazado',
                comentarios = %s
            WHERE id_autorizacion = %s
        """, (comentario, id_autorizacion))

        notificar(cur, session['id_usuario'],
                  f"Registro de {sol['tipo_solicitud']} (ref: #{sol['id_referencia']}) rechazado. Motivo: {comentario}")

        mysql.connection.commit()
        cur.close()

        return jsonify({'ok': True, 'mensaje': 'Solicitud rechazada.'})

    except Exception as e:
        mysql.connection.rollback()
        cur.close()
        return jsonify({'ok': False, 'mensaje': str(e)}), 500