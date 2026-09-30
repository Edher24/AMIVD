# Adriana Nicole Guzman Ahuatzi
# Rutas para la página de inicio: notificaciones, digitalización de documentos, expediente SIRED
from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for, send_file
from extensiones import mysql, notificar
from datetime import datetime
import os, io
from werkzeug.utils import secure_filename

principal = Blueprint('principal', __name__)


def login_requerido(f):
    from functools import wraps
    @wraps(f)
    def decorador(*args, **kwargs):
        if 'id_usuario' not in session:
            return redirect(url_for('auth.iniciarSesion'))
        return f(*args, **kwargs)
    return decorador


# ── Página de inicio ──────────────────────────────
@principal.route("/paginaInicio")
@login_requerido
def paginaInicio():
    return render_template("paginaInicio/paginaInicio.html")


# ══════════════════════════════════════════════════
# NOTIFICACIONES
# ══════════════════════════════════════════════════

@principal.route("/notificaciones")
@login_requerido
def notificaciones():
    fecha_filtro = request.args.get('fecha', '')
    cur = mysql.connection.cursor()
    if fecha_filtro:
        cur.execute("""
            SELECT id_notificacion, mensaje, fecha, leida
            FROM notificacion
            WHERE id_usuario = %s AND DATE(fecha) = %s
            ORDER BY fecha DESC
        """, (session['id_usuario'], fecha_filtro))
    else:
        cur.execute("""
            SELECT id_notificacion, mensaje, fecha, leida
            FROM notificacion
            WHERE id_usuario = %s
            ORDER BY fecha DESC
        """, (session['id_usuario'],))
    filas = cur.fetchall()
    cur.close()

    notifs = [
        {
            'id':      f['id_notificacion'],
            'mensaje': f['mensaje'],
            'leida':   bool(f['leida']),
            'fecha':   f['fecha'].strftime('%d/%m/%Y %H:%M') if f['fecha'] else ''
        }
        for f in filas
    ]
    sin_nuevas = all(n['leida'] for n in notifs) if notifs else True
    return render_template("paginaInicio/notificaciones.html",
                           notificaciones=notifs, fecha_filtro=fecha_filtro, sin_nuevas=sin_nuevas)


@principal.route("/notificaciones/marcar_todas", methods=["POST"])
@login_requerido
def marcar_todas_leidas():
    cur = mysql.connection.cursor()
    cur.execute("UPDATE notificacion SET leida = 1 WHERE id_usuario = %s", (session['id_usuario'],))
    mysql.connection.commit()
    cur.close()
    return jsonify({'ok': True})


@principal.route("/notificaciones/marcar/<int:id_notif>", methods=["POST"])
@login_requerido
def marcar_leida(id_notif):
    cur = mysql.connection.cursor()
    cur.execute("UPDATE notificacion SET leida = 1 WHERE id_notificacion = %s AND id_usuario = %s",
                (id_notif, session['id_usuario']))
    mysql.connection.commit()
    cur.close()
    return jsonify({'ok': True})


# ══════════════════════════════════════════════════
# DIGITALIZAR DOCUMENTOS
# ══════════════════════════════════════════════════

@principal.route("/digitalizarDocumentos")
@login_requerido
def digitalizar():
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT fd.id_formato, fd.nombre_archivo, fd.tipo, fd.fecha_subida, fd.ruta,
               CONCAT(j.apellido_paterno,' ',j.apellido_materno,' ',j.nombres) AS nombre_persona
        FROM formato_digital fd
        JOIN jugador j ON j.id_jugador = fd.id_jugador
        ORDER BY fd.fecha_subida DESC
    """)
    filas = cur.fetchall()
    cur.close()
    documentos = [
        {
            'id':      f['id_formato'],
            'nombre':  f['nombre_archivo'],
            'tipo':    f['tipo'],
            'fecha':   f['fecha_subida'].strftime('%d/%m/%Y') if f['fecha_subida'] else '',
            'ruta':    f['ruta'],
            'persona': f['nombre_persona'],
        }
        for f in filas
    ]
    return render_template("paginaInicio/digitalizarDocumentos.html", documentos=documentos)


@principal.route("/digitalizarDocumentos/subir", methods=["POST"])
@login_requerido
def subir_documento():
    tipo         = request.form.get('tipoDocumento')
    archivo      = request.files.get('archivo')
    id_persona   = request.form.get('id_persona')
    tipo_persona = request.form.get('tipo_persona', 'jugador')

    if not tipo or not archivo or not id_persona:
        return jsonify({'ok': False, 'mensaje': 'Datos incompletos'}), 400

    nombre_seguro = secure_filename(archivo.filename)
    ext = nombre_seguro.rsplit('.', 1)[-1].lower()
    if ext not in ('png', 'pdf', 'jpg', 'jpeg'):
        return jsonify({'ok': False, 'mensaje': 'Solo PNG, JPG y PDF'}), 400

    archivo.seek(0, 2)
    tamano = archivo.tell()
    archivo.seek(0)
    if tamano > 5 * 1024 * 1024:
        return jsonify({'ok': False, 'mensaje': 'Máximo 5 MB'}), 400

    carpeta = os.path.join('static', 'uploads', f'{tipo_persona}_{id_persona}')
    os.makedirs(carpeta, exist_ok=True)
    ruta = os.path.join(carpeta, nombre_seguro)
    archivo.save(ruta)

    cur = mysql.connection.cursor()

    if tipo_persona == 'entrenador':
        cur.execute("""
            SELECT CONCAT(apellido_paterno,' ',apellido_materno,' ',nombres) AS nombre
            FROM entrenador WHERE id_entrenador = %s
        """, (id_persona,))
    elif tipo_persona == 'arbitro':
        cur.execute("""
            SELECT CONCAT(apellido_paterno,' ',apellido_materno,' ',nombres) AS nombre
            FROM arbitro WHERE id_arbitro = %s
        """, (id_persona,))
    else:
        cur.execute("""
            SELECT CONCAT(apellido_paterno,' ',apellido_materno,' ',nombres) AS nombre
            FROM jugador WHERE id_jugador = %s
        """, (id_persona,))

    persona = cur.fetchone()
    nombre_persona = persona['nombre'] if persona else '—'

    id_jugador_ref = id_persona

    cur.execute("""
        INSERT INTO formato_digital (id_jugador, nombre_archivo, ruta, tipo, fecha_subida)
        VALUES (%s, %s, %s, %s, NOW())
    """, (id_jugador_ref, nombre_seguro, ruta, tipo))
    mysql.connection.commit()
    nuevo_id = cur.lastrowid
    notificar(cur, session['id_usuario'],
              f"Documento '{nombre_seguro}' ({tipo}) digitalizado para {nombre_persona}.")
    mysql.connection.commit()
    cur.close()

    return jsonify({
        'ok': True, 'id': nuevo_id, 'nombre': nombre_seguro,
        'tamano': _formatear_tamano(tamano), 'tipo': tipo,
        'fecha': datetime.now().strftime('%d/%m/%Y'), 'persona': nombre_persona
    })


@principal.route("/digitalizarDocumentos/eliminar/<int:id_doc>", methods=["POST"])
@login_requerido
def eliminar_documento(id_doc):
    cur = mysql.connection.cursor()
    cur.execute("SELECT ruta FROM formato_digital WHERE id_formato = %s", (id_doc,))
    fila = cur.fetchone()
    if not fila:
        cur.close()
        return jsonify({'ok': False, 'mensaje': 'No encontrado'}), 404
    if os.path.exists(fila['ruta']):
        os.remove(fila['ruta'])
    cur.execute("DELETE FROM formato_digital WHERE id_formato = %s", (id_doc,))
    mysql.connection.commit()
    notificar(cur, session['id_usuario'], f"Documento #{id_doc} eliminado del sistema.")
    mysql.connection.commit()
    cur.close()
    return jsonify({'ok': True})


# ══════════════════════════════════════════════════
# EXPEDIENTE SIRED
# ══════════════════════════════════════════════════

@principal.route("/expedientes")
@login_requerido
def expedientes():
    return render_template("paginaInicio/expedientes.html")


@principal.route("/expedientes/buscar")
@login_requerido
def buscar_expediente():
    """
    Busca por nombre o número de registro en las tres tablas:
    jugador (con expediente), entrenador y arbitro.
    Acepta un parámetro opcional 'tipo' para filtrar por:
    jugador, arbitro, entrenador.
    """
    termino = request.args.get('termino', '').strip()
    tipo_filtro = request.args.get('tipo', '').strip()

    if not termino:
        return jsonify({'ok': False, 'mensaje': 'Ingrese un nombre o número'}), 400

    cur = mysql.connection.cursor()
    resultados = []

    # ── Jugadores (con o sin expediente) ─────────
    if not tipo_filtro or tipo_filtro == 'jugador':
        try:
            cur.execute("""
                SELECT e.id_expediente, e.estatus, e.fecha_creacion,
                       j.id_jugador AS id_persona,
                       CONCAT(j.apellido_paterno,' ',j.apellido_materno,' ',j.nombres) AS nombre_completo,
                       j.numero_registro, j.categoria, 'jugador' AS tipo
                FROM jugador j
                LEFT JOIN expediente e ON e.id_jugador = j.id_jugador
                WHERE CONCAT(j.apellido_paterno,' ',j.apellido_materno,' ',j.nombres) LIKE %s
                   OR COALESCE(j.numero_registro,'') LIKE %s
                   OR CAST(j.id_jugador AS CHAR) LIKE %s
            """, (f'%{termino}%', f'%{termino}%', f'%{termino}%'))
        except Exception:
            cur.execute("""
                SELECT e.id_expediente, e.estatus, e.fecha_creacion,
                       j.id_jugador AS id_persona,
                       CONCAT(j.apellido_paterno,' ',j.apellido_materno,' ',j.nombres) AS nombre_completo,
                       NULL AS numero_registro, NULL AS categoria, 'jugador' AS tipo
                FROM jugador j
                LEFT JOIN expediente e ON e.id_jugador = j.id_jugador
                WHERE CONCAT(j.apellido_paterno,' ',j.apellido_materno,' ',j.nombres) LIKE %s
                   OR CAST(j.id_jugador AS CHAR) LIKE %s
            """, (f'%{termino}%', f'%{termino}%'))
        resultados += cur.fetchall()

    # ── Entrenadores ──────────────────────────────
    if not tipo_filtro or tipo_filtro == 'entrenador':
        try:
            cur.execute("""
                SELECT NULL AS id_expediente, 'activo' AS estatus, fecha_registro AS fecha_creacion,
                       id_entrenador AS id_persona,
                       CONCAT(apellido_paterno,' ',apellido_materno,' ',nombres) AS nombre_completo,
                       numero_registro, categoria, 'entrenador' AS tipo
                FROM entrenador
                WHERE CONCAT(apellido_paterno,' ',apellido_materno,' ',nombres) LIKE %s
                   OR COALESCE(numero_registro,'') LIKE %s
                   OR CAST(id_entrenador AS CHAR) LIKE %s
            """, (f'%{termino}%', f'%{termino}%', f'%{termino}%'))
            resultados += cur.fetchall()
        except Exception:
            pass

    # ── Árbitros ──────────────────────────────────
    if not tipo_filtro or tipo_filtro == 'arbitro':
        try:
            cur.execute("""
                SELECT NULL AS id_expediente, 'activo' AS estatus, fecha_registro AS fecha_creacion,
                       id_arbitro AS id_persona,
                       CONCAT(apellido_paterno,' ',apellido_materno,' ',nombres) AS nombre_completo,
                       numero_registro, categoria, 'arbitro' AS tipo
                FROM arbitro
                WHERE CONCAT(apellido_paterno,' ',apellido_materno,' ',nombres) LIKE %s
                   OR COALESCE(numero_registro,'') LIKE %s
                   OR CAST(id_arbitro AS CHAR) LIKE %s
            """, (f'%{termino}%', f'%{termino}%', f'%{termino}%'))
            resultados += cur.fetchall()
        except Exception:
            pass

    cur.close()

    if not resultados:
        return jsonify({'ok': False, 'mensaje': 'No se encontraron coincidencias'}), 404

    data = [
        {
            'id_expediente':   r['id_expediente'],
            'estatus':         r['estatus'],
            'fecha_creacion':  r['fecha_creacion'].strftime('%d/%m/%Y') if r['fecha_creacion'] else '—',
            'id_persona':      r['id_persona'],
            'nombre':          r['nombre_completo'],
            'numero_registro': r['numero_registro'] or '—',
            'categoria':       r['categoria'] or '—',
            'tipo':            r['tipo']
        }
        for r in resultados
    ]
    return jsonify({'ok': True, 'resultados': data})


@principal.route("/expedientes/generar", methods=["POST"])
@login_requerido
def generar_expediente():
    # CAMBIO: se recibe id_persona en lugar de id_expediente
    id_persona = request.json.get('id_persona')
    tipo       = request.json.get('tipo', 'jugador')

    if not id_persona:
        return jsonify({'ok': False, 'mensaje': 'Datos requeridos'}), 400

    cur = mysql.connection.cursor()

    if tipo == 'jugador':
        try:
            cur.execute("""
                SELECT e.id_expediente, e.estatus, e.fecha_creacion,
                       j.id_jugador, j.apellido_paterno, j.apellido_materno, j.nombres,
                       j.curp, j.fecha_nacimiento,
                       j.peso, j.estatura,
                       j.ocupacion, j.escolaridad, j.escuela,
                       j.telefono, j.celular, j.correo_electronico,
                       j.fotografia,
                       j.medicamentos,
                       j.numero_registro, j.categoria, j.tipo_sangre,
                       j.club, j.ligas_participa, j.vigencia, j.rama,
                       j.enfermedades_cronicas,
                       d.calle, d.numero_exterior, d.colonia, d.codigo_postal,
                       COALESCE(d.nombre_municipio, m.nombre) AS nombre_municipio,
                       eq.nombre_equipo, l.nombre_liga
                FROM jugador j
                LEFT JOIN expediente e ON e.id_jugador = j.id_jugador
                LEFT JOIN direccion d     ON d.id_jugador  = j.id_jugador
                LEFT JOIN cat_municipio m ON m.id_municipio = d.id_municipio
                LEFT JOIN equipo eq       ON eq.id_equipo   = j.id_equipo
                LEFT JOIN liga l          ON l.id_liga       = eq.id_liga
                WHERE j.id_jugador = %s
            """, (id_persona,))
        except Exception:
            cur.execute("""
                SELECT e.id_expediente, e.estatus, e.fecha_creacion,
                       j.id_jugador, j.apellido_paterno, j.apellido_materno, j.nombres,
                       j.curp, j.fecha_nacimiento,
                       j.peso, j.estatura,
                       j.ocupacion, j.escolaridad, j.escuela,
                       j.telefono, j.celular, j.correo_electronico,
                       j.fotografia, j.medicamentos,
                       NULL AS numero_registro, NULL AS categoria,
                       NULL AS tipo_sangre, NULL AS club,
                       NULL AS ligas_participa, NULL AS vigencia, NULL AS rama,
                       j.enfermedades_cronicas,
                       d.calle, d.numero_exterior, d.colonia, d.codigo_postal,
                       m.nombre AS nombre_municipio,
                       NULL AS nombre_equipo, NULL AS nombre_liga
                FROM jugador j
                LEFT JOIN expediente e ON e.id_jugador = j.id_jugador
                LEFT JOIN direccion d     ON d.id_jugador  = j.id_jugador
                LEFT JOIN cat_municipio m ON m.id_municipio = d.id_municipio
                WHERE j.id_jugador = %s
            """, (id_persona,))

    elif tipo == 'entrenador':
        cur.execute("""
            SELECT id_entrenador AS id_expediente, 'activo' AS estatus,
                   fecha_registro AS fecha_creacion,
                   id_entrenador, apellido_paterno, apellido_materno, nombres,
                   curp, fecha_nacimiento, numero_registro, categoria,
                   tipo_sangre, peso, estatura,
                   club, ligas_participa, vigencia, rama,
                   enfermedades_cronicas, medicamentos,
                   ocupacion, escolaridad, escuela,
                   telefono, celular, correo_electronico, fotografia,
                   NULL AS calle, NULL AS numero_exterior,
                   NULL AS colonia, NULL AS codigo_postal,
                   NULL AS nombre_municipio,
                   NULL AS nombre_equipo, NULL AS nombre_liga,
                   cedula, especialidad
            FROM entrenador WHERE id_entrenador = %s
        """, (id_persona,))

    elif tipo == 'arbitro':
        cur.execute("""
            SELECT id_arbitro AS id_expediente, 'activo' AS estatus,
                   fecha_registro AS fecha_creacion,
                   id_arbitro, apellido_paterno, apellido_materno, nombres,
                   curp, fecha_nacimiento, numero_registro, categoria,
                   tipo_sangre, peso, estatura,
                   club, ligas_participa, vigencia, rama,
                   enfermedades_cronicas, medicamentos,
                   ocupacion, escolaridad, escuela,
                   telefono, celular, correo_electronico, fotografia,
                   NULL AS calle, NULL AS numero_exterior,
                   NULL AS colonia, NULL AS codigo_postal,
                   NULL AS nombre_municipio,
                   NULL AS nombre_equipo, NULL AS nombre_liga,
                   zona, licencia
            FROM arbitro WHERE id_arbitro = %s
        """, (id_persona,))
    else:
        cur.close()
        return jsonify({'ok': False, 'mensaje': 'Tipo inválido'}), 400

    fila = cur.fetchone()

    sanciones = []
    if tipo == 'jugador' and fila:
        try:
            cur.execute("""
                SELECT s.tipo_sancion, s.fecha_sancion, s.fecha_fin_sancion,
                       s.motivo, s.estatus, l.nombre_liga
                FROM sanciones s
                LEFT JOIN liga l ON l.id_liga = s.id_liga
                WHERE s.id_jugador = %s
                ORDER BY s.fecha_sancion DESC
            """, (fila['id_jugador'],))
            sanciones = cur.fetchall()
        except Exception:
            pass

    cur.close()

    if not fila:
        return jsonify({'ok': False, 'mensaje': 'Sin datos'}), 404

    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Expediente"

    titulo_font   = Font(bold=True, size=14, color="FFFFFF")
    titulo_fill   = PatternFill("solid", fgColor="7A0C0C")
    seccion_font  = Font(bold=True, size=11, color="7A0C0C")
    etiqueta_font = Font(bold=True)
    center        = Alignment(horizontal="center")

    def fila_titulo(ws, texto):
        ws.append([texto])
        cell = ws.cell(row=ws.max_row, column=1)
        cell.font = titulo_font
        cell.fill = titulo_fill
        cell.alignment = center
        ws.merge_cells(start_row=ws.max_row, start_column=1,
                       end_row=ws.max_row, end_column=2)

    def fila_seccion(ws, texto):
        ws.append([])
        ws.append([texto])
        cell = ws.cell(row=ws.max_row, column=1)
        cell.font = seccion_font

    def fila_dato(ws, etiqueta, valor):
        ws.append([etiqueta, str(valor) if valor is not None else '—'])
        ws.cell(row=ws.max_row, column=1).font = etiqueta_font

    tipo_label = {'jugador': 'Jugador', 'entrenador': 'Entrenador', 'arbitro': 'Árbitro'}

    fila_titulo(ws, "EXPEDIENTE SIRED — SISTEMA AVT")
    ws.append([])
    fila_dato(ws, "ID Expediente", fila['id_expediente'])
    fila_dato(ws, "Tipo",          tipo_label.get(tipo, tipo))
    fila_dato(ws, "Estatus",       fila['estatus'])
    fila_dato(ws, "Fecha Creación",str(fila['fecha_creacion']))

    fila_seccion(ws, "DATOS PERSONALES")
    fila_dato(ws, "Apellido Paterno",  fila['apellido_paterno'])
    fila_dato(ws, "Apellido Materno",  fila['apellido_materno'] or '—')
    fila_dato(ws, "Nombres",           fila['nombres'])
    fila_dato(ws, "CURP",              fila['curp'])
    fila_dato(ws, "Fecha Nacimiento",  str(fila['fecha_nacimiento']))
    fila_dato(ws, "Tipo Sangre",       fila.get('tipo_sangre') or '—')
    fila_dato(ws, "Peso (kg)",         fila['peso'] or '—')
    fila_dato(ws, "Estatura (m)",      fila['estatura'] or '—')
    fila_dato(ws, "No. Registro",      fila.get('numero_registro') or '—')
    fila_dato(ws, "Categoría",         fila.get('categoria') or '—')
    fila_dato(ws, "Vigencia",          fila.get('vigencia') or '—')
    fila_dato(ws, "Rama",              fila.get('rama') or '—')
    fila_dato(ws, "Ocupación",         fila.get('ocupacion') or '—')
    fila_dato(ws, "Escolaridad",       fila.get('escolaridad') or '—')
    fila_dato(ws, "Escuela",           fila.get('escuela') or '—')

    fila_seccion(ws, "CONTACTO")
    fila_dato(ws, "Teléfono",  fila.get('telefono') or '—')
    fila_dato(ws, "Celular",   fila.get('celular') or '—')
    fila_dato(ws, "Correo",    fila.get('correo_electronico') or '—')

    fila_seccion(ws, "DOMICILIO")
    fila_dato(ws, "Municipio",     fila.get('nombre_municipio') or '—')
    fila_dato(ws, "Calle",         fila.get('calle') or '—')
    fila_dato(ws, "Num. Exterior", fila.get('numero_exterior') or '—')
    fila_dato(ws, "Colonia",       fila.get('colonia') or '—')
    fila_dato(ws, "C.P.",          fila.get('codigo_postal') or '—')

    fila_seccion(ws, "INFORMACIÓN DEPORTIVA")
    fila_dato(ws, "Club",            fila.get('club') or '—')
    fila_dato(ws, "Equipo",          fila.get('nombre_equipo') or '—')
    fila_dato(ws, "Liga",            fila.get('nombre_liga') or '—')
    fila_dato(ws, "Ligas Participa", fila.get('ligas_participa') or '—')

    if tipo == 'entrenador':
        fila_dato(ws, "Cédula",      fila.get('cedula') or '—')
        fila_dato(ws, "Especialidad",fila.get('especialidad') or '—')
    elif tipo == 'arbitro':
        fila_dato(ws, "Licencia", fila.get('licencia') or '—')
        fila_dato(ws, "Zona",     fila.get('zona') or '—')

    fila_seccion(ws, "SALUD")
    enf = fila.get('enfermedades_cronicas')
    if enf is None or enf == 0 or enf == '0':
        enf_texto = 'NINGUNA'
    elif enf == 1:
        enf_texto = 'SÍ (ver expediente físico)'
    else:
        enf_texto = str(enf)
    fila_dato(ws, "Enfermedades Crónicas", enf_texto)
    fila_dato(ws, "Medicamentos",          fila.get('medicamentos') or 'NINGUNA')

    if sanciones:
        fila_seccion(ws, "SANCIONES")
        ws.append(["Tipo", "Liga", "Fecha", "Fecha Fin", "Motivo", "Estatus"])
        for cell in ws[ws.max_row]:
            cell.font = etiqueta_font
        for s in sanciones:
            ws.append([
                s['tipo_sancion'],
                s.get('nombre_liga') or '—',
                str(s['fecha_sancion']),
                str(s['fecha_fin_sancion']) if s['fecha_fin_sancion'] else '—',
                s['motivo'],
                s['estatus'],
            ])

    ws.column_dimensions['A'].width = 28
    ws.column_dimensions['B'].width = 40

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    return send_file(output,
                     mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                     as_attachment=True,
                     download_name=f"expediente_{id_persona}.xlsx")


# ── Utilidad ──────────────────────────────────────
def _formatear_tamano(bytes):
    if not bytes:
        return '0 Bytes'
    for unidad in ['Bytes', 'KB', 'MB', 'GB']:
        if bytes < 1024:
            return f"{bytes:.1f} {unidad}"
        bytes /= 1024
    return f"{bytes:.1f} GB"