# Adriana Nicole Guzman Ahuatzi
#01/04/2026
# Rutas para el módulo de registro: ligas, equipos, personas (jugadores, entrenadores, árbitros) y pagos
from flask import Blueprint, render_template, session, redirect, url_for, request, jsonify
from extensiones import mysql, notificar
import os
from werkzeug.utils import secure_filename

registro = Blueprint('registro', __name__, url_prefix="/registro")


def login_requerido(f):
    from functools import wraps
    @wraps(f)
    def decorador(*args, **kwargs):
        if 'id_usuario' not in session:
            return redirect(url_for('auth.iniciarSesion'))
        return f(*args, **kwargs)
    return decorador


# ── Menú general ──────────────────────────────────
@registro.route("/")
@login_requerido
def registroGeneral():
    return render_template("registro/registroGeneral.html")


# ══════════════════════════════════════════════════
# LIGA
# ══════════════════════════════════════════════════

@registro.route("/liga")
@login_requerido
def registroLiga():
    cur = mysql.connection.cursor()
    cur.execute("SELECT id_liga, nombre_liga, categoria FROM liga ORDER BY nombre_liga")
    ligas = cur.fetchall()
    cur.close()
    return render_template("registro/registroLiga.html", ligas=ligas)


@registro.route("/liga/guardar", methods=["POST"])
@login_requerido
def guardarLiga():
    nombre    = request.form.get('nombre_liga', '').strip().upper()
    categoria = request.form.get('categoria', '').strip().upper()
    if not nombre:
        return jsonify({'ok': False, 'mensaje': 'El nombre de la liga es obligatorio'}), 400
    cur = mysql.connection.cursor()
    try:
        cur.execute("SELECT id_liga FROM liga WHERE nombre_liga = %s", (nombre,))
        if cur.fetchone():
            cur.close()
            return jsonify({'ok': False, 'mensaje': 'Ya existe una liga con ese nombre'}), 400
        cur.execute("INSERT INTO liga (nombre_liga, categoria) VALUES (%s, %s)", (nombre, categoria))
        mysql.connection.commit()
        nuevo_id = cur.lastrowid
        notificar(cur, session['id_usuario'], f"Liga '{nombre}' registrada.")
        mysql.connection.commit()
        cur.close()
        return jsonify({'ok': True, 'mensaje': f'Liga "{nombre}" registrada correctamente.',
                        'id': nuevo_id, 'nombre': nombre, 'categoria': categoria})
    except Exception as e:
        mysql.connection.rollback()
        cur.close()
        return jsonify({'ok': False, 'mensaje': str(e)}), 500


@registro.route("/liga/eliminar/<int:id_liga>", methods=["POST"])
@login_requerido
def eliminarLiga(id_liga):
    cur = mysql.connection.cursor()
    try:
        cur.execute("DELETE FROM liga WHERE id_liga = %s", (id_liga,))
        mysql.connection.commit()
        notificar(cur, session['id_usuario'], f"Liga #{id_liga} eliminada.")
        mysql.connection.commit()
        cur.close()
        return jsonify({'ok': True})
    except Exception as e:
        mysql.connection.rollback()
        cur.close()
        return jsonify({'ok': False, 'mensaje': str(e)}), 500


# ══════════════════════════════════════════════════
# EQUIPO
# ══════════════════════════════════════════════════

@registro.route("/equipo")
@login_requerido
def registroEquipo():
    cur = mysql.connection.cursor()
    cur.execute("SELECT id_liga, nombre_liga, categoria FROM liga ORDER BY nombre_liga")
    ligas = cur.fetchall()
    cur.execute("""
        SELECT e.id_equipo, e.nombre_equipo, e.categoria, l.nombre_liga, l.id_liga
        FROM equipo e JOIN liga l ON l.id_liga = e.id_liga
        ORDER BY e.nombre_equipo
    """)
    equipos = cur.fetchall()
    cur.close()
    return render_template("registro/registroEquipo.html", ligas=ligas, equipos=equipos)


@registro.route("/equipo/guardar", methods=["POST"])
@login_requerido
def guardarEquipo():
    nombre    = request.form.get('nombre_equipo', '').strip().upper()
    id_liga   = request.form.get('id_liga')
    categoria = request.form.get('categoria', '').strip().upper()
    if not nombre or not id_liga:
        return jsonify({'ok': False, 'mensaje': 'Nombre y liga son obligatorios'}), 400
    cur = mysql.connection.cursor()
    try:
        cur.execute("SELECT id_equipo FROM equipo WHERE nombre_equipo = %s AND id_liga = %s",
                    (nombre, id_liga))
        if cur.fetchone():
            cur.close()
            return jsonify({'ok': False, 'mensaje': 'Ya existe ese equipo en esta liga'}), 400
        cur.execute("INSERT INTO equipo (id_liga, nombre_equipo, categoria) VALUES (%s, %s, %s)",
                    (id_liga, nombre, categoria))
        mysql.connection.commit()
        nuevo_id = cur.lastrowid
        cur.execute("SELECT nombre_liga FROM liga WHERE id_liga = %s", (id_liga,))
        liga = cur.fetchone()
        notificar(cur, session['id_usuario'],
                  f"Equipo '{nombre}' registrado en liga '{liga['nombre_liga'] if liga else id_liga}'.")
        mysql.connection.commit()
        cur.close()
        return jsonify({'ok': True, 'mensaje': f'Equipo "{nombre}" registrado correctamente.',
                        'id': nuevo_id, 'nombre': nombre, 'categoria': categoria,
                        'nombre_liga': liga['nombre_liga'] if liga else ''})
    except Exception as e:
        mysql.connection.rollback()
        cur.close()
        return jsonify({'ok': False, 'mensaje': str(e)}), 500


@registro.route("/equipo/eliminar/<int:id_equipo>", methods=["POST"])
@login_requerido
def eliminarEquipo(id_equipo):
    cur = mysql.connection.cursor()
    try:
        cur.execute("DELETE FROM equipo WHERE id_equipo = %s", (id_equipo,))
        mysql.connection.commit()
        notificar(cur, session['id_usuario'], f"Equipo #{id_equipo} eliminado.")
        mysql.connection.commit()
        cur.close()
        return jsonify({'ok': True})
    except Exception as e:
        mysql.connection.rollback()
        cur.close()
        return jsonify({'ok': False, 'mensaje': str(e)}), 500


# ══════════════════════════════════════════════════
# PAGO
# ══════════════════════════════════════════════════

@registro.route("/pago")
@login_requerido
def registroPago():
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT p.id_pago, p.fecha_pago, p.estatus, p.metodo_pago, p.referencia,
               'jugador' AS tipo_persona,
               CONCAT(j.apellido_paterno,' ',j.apellido_materno,' ',j.nombres) AS nombre_persona
        FROM pago p
        JOIN afiliacion a ON a.id_afiliacion = p.id_afiliacion
        JOIN jugador    j ON j.id_jugador    = a.id_jugador
        ORDER BY p.fecha_pago DESC
    """)
    pagos = cur.fetchall()
    cur.close()
    return render_template("registro/registroPago.html", pagos=pagos)


@registro.route("/pago/guardar", methods=["POST"])
@login_requerido
def guardarPago():
    id_jugador  = request.form.get('id_persona') or request.form.get('id_jugador')
    fecha_pago  = request.form.get('fecha_pago')
    estatus     = request.form.get('estatus', 'Pendiente')
    metodo_pago = request.form.get('metodo_pago', '').strip()
    referencia  = request.form.get('referencia', '').strip()
    if not id_jugador or not fecha_pago:
        return jsonify({'ok': False, 'mensaje': 'Jugador y fecha son obligatorios'}), 400
    cur = mysql.connection.cursor()
    try:
        cur.execute("""
            SELECT id_afiliacion FROM afiliacion
            WHERE id_jugador = %s ORDER BY fecha_afiliacion DESC LIMIT 1
        """, (id_jugador,))
        afil = cur.fetchone()
        if not afil:
            cur.execute("""
                INSERT INTO afiliacion
                    (id_jugador, id_club, id_vigencia, numero_registro,
                     ano_vigencia, fecha_afiliacion, fecha_vencimiento, estatus)
                VALUES (%s, 1, 1, %s, YEAR(NOW()), NOW(), DATE_ADD(NOW(), INTERVAL 1 YEAR), 'Activa')
            """, (id_jugador, f'REG-{id_jugador}-{fecha_pago}'))
            id_afiliacion = cur.lastrowid
        else:
            id_afiliacion = afil['id_afiliacion']

        # ── NUEVO: Verificar si ya existe un pago para esta afiliación y fecha ──
        cur.execute("""
            SELECT id_pago FROM pago
            WHERE id_afiliacion = %s AND fecha_pago = %s
        """, (id_afiliacion, fecha_pago))
        pago_existente = cur.fetchone()

        if pago_existente:
            # Actualizar el pago existente (no generar duplicado)
            cur.execute("""
                UPDATE pago
                SET estatus = %s, metodo_pago = %s, referencia = %s
                WHERE id_pago = %s
            """, (estatus, metodo_pago or None, referencia or None, pago_existente['id_pago']))
            mysql.connection.commit()
            nuevo_id = pago_existente['id_pago']
            mensaje = 'Pago actualizado correctamente.'
        else:
            # Insertar nuevo pago
            cur.execute("""
                INSERT INTO pago (id_afiliacion, fecha_pago, estatus, metodo_pago, referencia)
                VALUES (%s, %s, %s, %s, %s)
            """, (id_afiliacion, fecha_pago, estatus, metodo_pago or None, referencia or None))
            mysql.connection.commit()
            nuevo_id = cur.lastrowid
            mensaje = 'Pago registrado correctamente.'

        notificar(cur, session['id_usuario'],
                  f"Pago #{nuevo_id} registrado para jugador #{id_jugador} — estatus: {estatus}.")
        mysql.connection.commit()
        cur.close()
        return jsonify({'ok': True, 'mensaje': mensaje, 'id': nuevo_id})
    except Exception as e:
        mysql.connection.rollback()
        cur.close()
        return jsonify({'ok': False, 'mensaje': str(e)}), 500


@registro.route("/pago/actualizar/<int:id_pago>", methods=["POST"])
@login_requerido
def actualizarPago(id_pago):
    estatus = request.form.get('estatus')
    if estatus not in ('Pendiente', 'Completado', 'Cancelado'):
        return jsonify({'ok': False, 'mensaje': 'Estatus inválido'}), 400
    cur = mysql.connection.cursor()
    try:
        cur.execute("UPDATE pago SET estatus = %s WHERE id_pago = %s", (estatus, id_pago))
        mysql.connection.commit()
        notificar(cur, session['id_usuario'], f"Pago #{id_pago} actualizado a '{estatus}'.")
        mysql.connection.commit()
        cur.close()
        return jsonify({'ok': True})
    except Exception as e:
        mysql.connection.rollback()
        cur.close()
        return jsonify({'ok': False, 'mensaje': str(e)}), 500


# ══════════════════════════════════════════════════
# PERSONA (jugador / entrenador / árbitro)
# ══════════════════════════════════════════════════

@registro.route("/persona")
@login_requerido
def registroPersona():
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT e.id_equipo, e.nombre_equipo, e.categoria, l.nombre_liga
        FROM equipo e JOIN liga l ON l.id_liga = e.id_liga
        ORDER BY e.nombre_equipo
    """)
    equipos = cur.fetchall()
    cur.execute("SELECT id_municipio, nombre FROM cat_municipio ORDER BY nombre")
    municipios = cur.fetchall()

    cur.execute("SELECT COUNT(*) AS total FROM jugador")
    sig_jugador = cur.fetchone()['total'] + 1

    try:
        cur.execute("SELECT COUNT(*) AS total FROM entrenador")
        sig_entrenador = cur.fetchone()['total'] + 1
    except Exception:
        sig_entrenador = 1

    try:
        cur.execute("SELECT COUNT(*) AS total FROM arbitro")
        sig_arbitro = cur.fetchone()['total'] + 1
    except Exception:
        sig_arbitro = 1

    cur.close()
    return render_template(
        "registro/registroPersona.html",
        equipos=equipos,
        municipios=municipios,
        sig_jugador=f"JUG-{sig_jugador:03d}",
        sig_entrenador=f"ENT-{sig_entrenador:03d}",
        sig_arbitro=f"ARB-{sig_arbitro:03d}",
    )


@registro.route("/persona/siguiente_registro")
@login_requerido
def siguienteRegistro():
    tipo = request.args.get('tipo', '').strip()
    cur = mysql.connection.cursor()
    try:
        if tipo == 'jugador':
            cur.execute("SELECT COUNT(*) AS total FROM jugador")
            prefijo = 'JUG'
        elif tipo == 'entrenador':
            cur.execute("SELECT COUNT(*) AS total FROM entrenador")
            prefijo = 'ENT'
        elif tipo == 'arbitro':
            cur.execute("SELECT COUNT(*) AS total FROM arbitro")
            prefijo = 'ARB'
        else:
            cur.close()
            return jsonify({'ok': False}), 400
        total = cur.fetchone()['total']
        cur.close()
        return jsonify({'ok': True, 'numero': f"{prefijo}-{total + 1:03d}"})
    except Exception as e:
        cur.close()
        return jsonify({'ok': False, 'mensaje': str(e)}), 500


def generar_numero_registro(cur, tipo):
    """
    Genera el siguiente número de registro para jugador, arbitro o entrenador.
    Usa MAX sobre el campo numero_registro para evitar colisiones aunque haya
    huecos o inserciones fallidas previas.
    """
    if tipo == 'jugador':
        tabla, prefijo = 'jugador', 'JUG'
    elif tipo == 'entrenador':
        tabla, prefijo = 'entrenador', 'ENT'
    elif tipo == 'arbitro':
        tabla, prefijo = 'arbitro', 'ARB'
    else:
        raise ValueError(f"Tipo inválido: {tipo}")
 
    cur.execute(
        f"SELECT MAX(CAST(SUBSTRING(numero_registro, 5) AS UNSIGNED)) AS ultimo "
        f"FROM {tabla} WHERE numero_registro LIKE %s",
        (f"{prefijo}-%",)
    )
    row    = cur.fetchone()
    ultimo = row['ultimo'] if row and row['ultimo'] else 0
    return f"{prefijo}-{ultimo + 1:03d}"
 

@registro.route("/persona/guardar", methods=["POST"])
@login_requerido
def guardarPersona():
    data = request.form
    tipo = data.get('tipo_persona', '').strip()
    foto = request.files.get('fotoPersona')

    if tipo not in ('jugador', 'arbitro', 'entrenador'):
        return jsonify({'ok': False, 'mensaje': 'Tipo de persona inválido'}), 400

    vigencia = ','.join(request.form.getlist('vigencia'))

    ruta_foto = None
    if foto and foto.filename:
        nombre_foto  = secure_filename(foto.filename)
        carpeta_foto = os.path.join('static', 'uploads', 'fotos', tipo)
        os.makedirs(carpeta_foto, exist_ok=True)
        ruta_foto    = os.path.join(carpeta_foto, nombre_foto)
        foto.save(ruta_foto)

    firma_base64_guardar = None
    firma_b64 = data.get('firma_base64', '').strip()
    if firma_b64 and firma_b64.startswith('data:image/png;base64,'):
        firma_base64_guardar = firma_b64

    cur = mysql.connection.cursor()
    try:
        numero_registro = generar_numero_registro(cur, tipo)

        nombre_municipio = data.get('municipio', '').strip().upper()
        id_municipio = 1
        if nombre_municipio:
            cur.execute("SELECT id_municipio FROM cat_municipio WHERE UPPER(nombre) = %s",
                        (nombre_municipio,))
            mun = cur.fetchone()
            if mun:
                id_municipio = mun['id_municipio']
            else:
                cur.execute("INSERT INTO cat_municipio (id_estado, nombre) VALUES (1, %s)",
                            (nombre_municipio,))
                id_municipio = cur.lastrowid

        id_equipo = data.get('id_equipo') or None

        apellido_paterno    = data.get('apellido_paterno', '').upper()
        apellido_materno    = data.get('apellido_materno', '').upper()
        nombres             = data.get('nombres', '').upper()
        curp                = data.get('curp', '').upper()
        fecha_nacimiento    = data.get('fecha_nacimiento')
        lugar_nacimiento    = data.get('lugar_nacimiento', '').upper() or None
        nacionalidad        = data.get('nacionalidad', 'MEXICANA').upper()
        peso                = data.get('peso') or None
        estatura            = data.get('estatura') or None
        tipo_sangre         = data.get('tipo_sangre') or None
        ocupacion           = data.get('ocupacion', '').upper() or None
        escolaridad         = data.get('escolaridad', '').upper() or None
        escuela             = data.get('escuela', '').upper() or None
        telefono            = data.get('telefono') or None
        celular             = data.get('celular') or None
        correo              = data.get('email') or data.get('correo_electronico') or None
        enfermedades        = data.get('enfermedades_cronicas', 'NINGUNA').upper() or 'NINGUNA'
        medicamentos        = data.get('medicamentos', 'NINGUNA').upper() or 'NINGUNA'
        club                = data.get('club', '').upper() or None
        categoria           = data.get('categoria') or None
        rama                = data.get('rama') or None
        ligas_participa     = data.get('ligas_participa', '').upper() or None

        if tipo == 'jugador':
            try:
                cur.execute("""
                    INSERT INTO jugador (
                        apellido_paterno, apellido_materno, nombres,
                        numero_registro, curp, vigencia,
                        fecha_nacimiento, lugar_nacimiento, nacionalidad,
                        peso, estatura, tipo_sangre,
                        ocupacion, escolaridad, escuela,
                        telefono, celular, correo_electronico,
                        enfermedades_cronicas, medicamentos,
                        club, categoria, rama, ligas_participa, fotografia, firma_base64
                    ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                """, (
                    apellido_paterno, apellido_materno, nombres,
                    numero_registro, curp, vigencia or None,
                    fecha_nacimiento, lugar_nacimiento, nacionalidad,
                    peso, estatura, tipo_sangre,
                    ocupacion, escolaridad, escuela,
                    telefono, celular, correo,
                    enfermedades, medicamentos,
                    club, categoria, rama, ligas_participa, ruta_foto, firma_base64_guardar,
                ))
            except Exception:
                mysql.connection.rollback()
                cur.execute("""
                    INSERT INTO jugador (
                        apellido_paterno, apellido_materno, nombres,
                        curp, fecha_nacimiento, lugar_nacimiento, nacionalidad,
                        peso, estatura,
                        ocupacion, escolaridad, escuela,
                        telefono, celular, correo_electronico,
                        medicamentos, fotografia, firma_base64
                    ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                """, (
                    apellido_paterno, apellido_materno, nombres,
                    curp, fecha_nacimiento, lugar_nacimiento, nacionalidad,
                    peso, estatura,
                    ocupacion, escolaridad, escuela,
                    telefono, celular, correo,
                    medicamentos, ruta_foto, firma_base64_guardar,
                ))

            id_persona = cur.lastrowid

            try:
                cur.execute("""
                    INSERT INTO direccion
                        (id_jugador, id_municipio, nombre_municipio,
                         calle, numero_exterior, colonia, codigo_postal)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (
                    id_persona, id_municipio, nombre_municipio,
                    data.get('calle', '').upper(),
                    data.get('numero_exterior', '') or None,
                    data.get('colonia', '').upper(),
                    data.get('codigo_postal', '')
                ))
            except Exception:
                cur.execute("""
                    INSERT INTO direccion
                        (id_jugador, id_municipio,
                         calle, numero_exterior, colonia, codigo_postal)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (
                    id_persona, id_municipio,
                    data.get('calle', '').upper(),
                    data.get('numero_exterior', '') or None,
                    data.get('colonia', '').upper(),
                    data.get('codigo_postal', '')
                ))

            cur.execute("""
                INSERT INTO expediente (id_jugador, estatus, fecha_creacion)
                VALUES (%s, 'activo', NOW())
            """, (id_persona,))

            nombre_padre = data.get('nombre_padre', '').strip()
            if nombre_padre:
                cur.execute("""
                    INSERT INTO tutor_padre
                        (id_jugador, nombre_completo, celular, correo_electronico, curp_tutor)
                    VALUES (%s, %s, %s, %s, %s)
                """, (
                    id_persona,
                    nombre_padre.upper(),
                    data.get('celular_padre') or None,
                    data.get('email_padre') or None,
                    data.get('curp_tutor', '').upper() or None
                ))

        elif tipo == 'entrenador':
            cur.execute("""
                INSERT INTO entrenador (
                    id_equipo,
                    apellido_paterno, apellido_materno, nombres,
                    numero_registro, curp, vigencia,
                    fecha_nacimiento, lugar_nacimiento, nacionalidad,
                    peso, estatura, tipo_sangre,
                    ocupacion, escolaridad, escuela,
                    telefono, celular, correo_electronico,
                    enfermedades_cronicas, medicamentos,
                    club, categoria, rama, ligas_participa, fotografia,
                    cedula, especialidad, firma_base64
                ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """, (
                id_equipo,
                apellido_paterno, apellido_materno, nombres,
                numero_registro, curp, vigencia or None,
                fecha_nacimiento, lugar_nacimiento, nacionalidad,
                peso, estatura, tipo_sangre,
                ocupacion, escolaridad, escuela,
                telefono, celular, correo,
                enfermedades, medicamentos,
                club, categoria, rama, ligas_participa, ruta_foto,
                data.get('cedula') or None,
                data.get('especialidad') or None, firma_base64_guardar,
            ))
            id_persona = cur.lastrowid

        elif tipo == 'arbitro':
            cur.execute("""
                INSERT INTO arbitro (
                    id_equipo,
                    apellido_paterno, apellido_materno, nombres,
                    numero_registro, curp, vigencia,
                    fecha_nacimiento, lugar_nacimiento, nacionalidad,
                    peso, estatura, tipo_sangre,
                    ocupacion, escolaridad, escuela,
                    telefono, celular, correo_electronico,
                    enfermedades_cronicas, medicamentos,
                    club, categoria, rama, ligas_participa, fotografia,
                    zona, licencia, firma_base64
                ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """, (
                id_equipo,
                apellido_paterno, apellido_materno, nombres,
                numero_registro, curp, vigencia or None,
                fecha_nacimiento, lugar_nacimiento, nacionalidad,
                peso, estatura, tipo_sangre,
                ocupacion, escolaridad, escuela,
                telefono, celular, correo,
                enfermedades, medicamentos,
                club, categoria, rama, ligas_participa, ruta_foto,
                data.get('zona') or None,
                data.get('licencia') or None,
                firma_base64_guardar,
            ))
            id_persona = cur.lastrowid

        cur.execute("""
            INSERT INTO autorizacion_pendiente
                (tipo_solicitud, id_referencia, fecha_solicitud, estatus)
            VALUES (%s, %s, NOW(), 'Pendiente')
        """, (tipo, id_persona))

        nombre_completo = f"{apellido_paterno} {nombres}".strip()
        notificar(cur, session['id_usuario'],
                  f"Nuevo registro de {tipo}: {nombre_completo} ({numero_registro}). "
                  f"Solicitud de autorización creada.")

        mysql.connection.commit()
        cur.close()
        return jsonify({
            'ok':              True,
            'mensaje':         f'{tipo.capitalize()} registrado correctamente.',
            'id':              id_persona,
            'numero_registro': numero_registro,
        })

    except Exception as e:
        mysql.connection.rollback()
        cur.close()
        return jsonify({'ok': False, 'mensaje': str(e)}), 500