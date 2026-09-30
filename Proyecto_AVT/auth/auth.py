# Adriana Nicole Guzman Ahuatzi
#01/04/2026
# Rutas de autenticación: inicio de sesión, nuevo usuario, cierre de sesión, registro externo.
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from extensiones import mysql, bcrypt, notificar
import os
from werkzeug.utils import secure_filename

auth = Blueprint('auth', __name__)


# ══════════════════════════════════════════════════
# INICIO DE SESIÓN
# ══════════════════════════════════════════════════

@auth.route("/")
@auth.route("/iniciarSesion", methods=["GET"])
def index():
    return render_template("auth/iniciarSesion.html")


@auth.route("/iniciarSesion", methods=["POST"])
def iniciarSesion():
    nombreUsuario = request.form["nombreUsuario"]
    password      = request.form["password"]
    cur = mysql.connection.cursor()
    
    # Buscar solo por nombre de usuario
    cur.execute("SELECT * FROM usuario WHERE nombre_usuario = %s", (nombreUsuario,))
    usuario = cur.fetchone()
    cur.close()
    
    # Caso 1: Usuario no existe
    if not usuario:
        flash("El usuario no existe", "error")
        return redirect(url_for("auth.iniciarSesion"))
    
    # Caso 2: Usuario inactivo
    if not usuario['activo']:
        flash("El usuario está inactivo. Contacta al administrador.", "error")
        return redirect(url_for("auth.iniciarSesion"))
    
    # Caso 3: Contraseña incorrecta
    if not bcrypt.check_password_hash(usuario['password'], password):
        flash("La contraseña es incorrecta", "error")
        return redirect(url_for("auth.iniciarSesion"))
    
    # Login exitoso
    session['id_usuario']      = usuario['id_usuario']
    session['nombre_usuario']  = usuario['nombre_usuario']
    session['nombre_completo'] = usuario['nombre_completo']
    session['rol']             = usuario['rol']
    cur2 = mysql.connection.cursor()
    notificar(cur2, usuario['id_usuario'], "Inicio de sesión desde el sistema.")
    mysql.connection.commit()
    cur2.close()
    return redirect(url_for("principal.paginaInicio"))


# ══════════════════════════════════════════════════
# NUEVO USUARIO
# ══════════════════════════════════════════════════

@auth.route("/nuevoUsuario", methods=["GET", "POST"])
@auth.route("/nuevoUsuario", methods=["GET", "POST"])
def nuevoUsuario():
    if request.method == "POST":
        nombre_usuario  = request.form["nombre_usuario"]
        nombre_completo = request.form["nombre_completo"]
        email           = request.form["email"]
        password        = request.form["password"]
        rol             = request.form["rol"]
        
        # Validar que el rol sea válido (sin 'Delegado')
        if rol not in ('Presidente', 'Secretaria', 'Administrador'):
            flash("Rol inválido", "error")
            return redirect(url_for("auth.nuevoUsuario"))
        
        cur = mysql.connection.cursor()
        
        # Verificar si el nombre de usuario ya existe
        cur.execute("SELECT id_usuario FROM usuario WHERE nombre_usuario = %s", (nombre_usuario,))
        if cur.fetchone():
            cur.close()
            flash("El nombre de usuario ya está registrado", "error")
            return redirect(url_for("auth.nuevoUsuario"))
        
        # Verificar si el email ya existe
        cur.execute("SELECT id_usuario FROM usuario WHERE email = %s", (email,))
        if cur.fetchone():
            cur.close()
            flash("El correo electrónico ya está registrado", "error")
            return redirect(url_for("auth.nuevoUsuario"))
        
        # Insertar nuevo usuario
        hashed = bcrypt.generate_password_hash(password).decode('utf-8')
        try:
            cur.execute("""
                INSERT INTO usuario (nombre_usuario, password, rol, nombre_completo, email, activo)
                VALUES (%s, %s, %s, %s, %s, 1)
            """, (nombre_usuario, hashed, rol, nombre_completo, email))
            mysql.connection.commit()
            nuevo_id = cur.lastrowid
            notificar(cur, nuevo_id, f"Bienvenido al sistema AVT. Tu cuenta fue creada con rol: {rol}.")
            mysql.connection.commit()
            cur.close()
            flash("Usuario registrado exitosamente", "success")
            if 'id_usuario' in session:                          # ← NUEVO
                return redirect(url_for("auth.nuevoUsuario"))    # ← NUEVO
            return redirect(url_for("auth.iniciarSesion"))
        except Exception:
            mysql.connection.rollback()
            cur.close()
            flash("Error al registrar el usuario. Intenta de nuevo.", "error")
            return redirect(url_for("auth.nuevoUsuario"))
    return render_template("auth/nuevoUsuario.html")

# ══════════════════════════════════════════════════
# CERRAR SESIÓN
# ══════════════════════════════════════════════════

@auth.route("/cerrarSesion")
def cerrarSesion():
    session.clear()
    return redirect(url_for("auth.iniciarSesion"))


# ══════════════════════════════════════════════════
# ACCESO EXTERNO
# ══════════════════════════════════════════════════
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
 

@auth.route("/accesoExterno", methods=["GET"])
def accesoExterno():
    return render_template("auth/accesoExterno.html")


@auth.route("/accesoExterno", methods=["POST"])
def accesoExternoPost():
    nombre_completo = request.form.get('nombre_completo', '').strip()
    email           = request.form.get('email', '').strip()
    if not nombre_completo or not email:
        flash("Nombre y correo son obligatorios.", "error")
        return redirect(url_for("auth.accesoExterno"))
    session['ext_nombre'] = nombre_completo
    session['ext_email']  = email
    return redirect(url_for("auth.formularioExterno"))


@auth.route("/registroExterno", methods=["GET"])
def formularioExterno():
    if 'ext_nombre' not in session:
        return redirect(url_for("auth.accesoExterno"))
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT e.id_equipo, e.nombre_equipo, e.categoria, l.nombre_liga
        FROM equipo e JOIN liga l ON l.id_liga = e.id_liga
        ORDER BY e.nombre_equipo
    """)
    equipos = cur.fetchall()
    cur.close()
    return render_template("registro/registroExterno.html",
                           equipos=equipos,
                           ext_nombre=session['ext_nombre'],
                           ext_email=session['ext_email'])


@auth.route("/registroExterno/guardar", methods=["POST"])
def guardarRegistroExterno():
    if 'ext_nombre' not in session:
        return redirect(url_for("auth.accesoExterno"))

    data  = request.form
    tipo  = data.get('tipo_persona', '').strip()
    email = session.get('ext_email', '')

    if tipo not in ('jugador', 'arbitro', 'entrenador'):
        return jsonify({'ok': False, 'mensaje': 'Tipo de persona inválido'}), 400

    # ── Fotografía ────────────────────────────────────────────────
    foto      = request.files.get('fotoPersona')
    ruta_foto = None
    if foto and foto.filename:
        nombre_foto  = secure_filename(foto.filename)
        carpeta_foto = os.path.join('static', 'uploads', 'fotos', tipo)
        os.makedirs(carpeta_foto, exist_ok=True)
        ruta_foto    = os.path.join(carpeta_foto, nombre_foto)
        foto.save(ruta_foto)

    # ── Firma digital (guardada como base64 en BD) ────────────────
    firma_base64_guardar = None
    firma_b64 = data.get('firma_base64', '').strip()
    if firma_b64 and firma_b64.startswith('data:image/png;base64,'):
        firma_base64_guardar = firma_b64

    vigencia = ','.join(request.form.getlist('vigencia'))

    cur = mysql.connection.cursor()
    try:
       
        numero_registro = generar_numero_registro(cur, tipo)

        # ── Resolver municipio por nombre ─────────────────────────
        nombre_municipio = data.get('municipio', '').strip().upper()
        id_municipio = 1
        if nombre_municipio:
            cur.execute("SELECT id_municipio FROM cat_municipio WHERE nombre = %s",
                        (nombre_municipio,))
            mun = cur.fetchone()
            if mun:
                id_municipio = mun['id_municipio']
            else:
                cur.execute("INSERT INTO cat_municipio (id_estado, nombre) VALUES (1, %s)",
                            (nombre_municipio,))
                id_municipio = cur.lastrowid

        # ── Campos comunes a las tres tablas ──────────────────────
        apellido_paterno = data.get('apellido_paterno', '').upper()
        apellido_materno = data.get('apellido_materno', '').upper()
        nombres          = data.get('nombres', '').upper()
        curp             = data.get('curp', '').upper()
        fecha_nacimiento = data.get('fecha_nacimiento')
        lugar_nacimiento = data.get('lugar_nacimiento', '').upper() or None
        nacionalidad     = data.get('nacionalidad', 'MEXICANA').upper()
        peso             = data.get('peso') or None
        estatura         = data.get('estatura') or None
        tipo_sangre      = data.get('tipo_sangre') or None
        ocupacion        = data.get('ocupacion', '').upper() or None
        escolaridad      = data.get('escolaridad', '').upper() or None
        escuela          = data.get('escuela', '').upper() or None
        telefono         = data.get('telefono') or None
        celular          = data.get('celular') or None
        correo           = email
        enfermedades     = data.get('enfermedades_cronicas', 'NINGUNA').upper() or 'NINGUNA'
        medicamentos     = data.get('medicamentos', 'NINGUNA').upper() or 'NINGUNA'
        club             = data.get('club', '').upper() or None
        categoria        = data.get('categoria') or None
        rama             = data.get('rama') or None
        ligas_participa  = data.get('ligas_participa', '').upper() or None

        # ── INSERT por tipo ───────────────────────────────────────
        if tipo == 'jugador':
            cur.execute("""
                INSERT INTO jugador (
                    apellido_paterno, apellido_materno, nombres,
                    numero_registro, curp, vigencia,
                    fecha_nacimiento, lugar_nacimiento, nacionalidad,
                    peso, estatura, tipo_sangre,
                    ocupacion, escolaridad, escuela,
                    telefono, celular, correo_electronico,
                    enfermedades_cronicas, medicamentos,
                    club, categoria, rama, ligas_participa,
                    fotografia, firma_base64
                ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """, (
                apellido_paterno, apellido_materno, nombres,
                numero_registro, curp, vigencia or None,
                fecha_nacimiento, lugar_nacimiento, nacionalidad,
                peso, estatura, tipo_sangre,
                ocupacion, escolaridad, escuela,
                telefono, celular, correo,
                enfermedades, medicamentos,
                club, categoria, rama, ligas_participa,
                ruta_foto, firma_base64_guardar,
            ))
            id_persona = cur.lastrowid

            try:
                cur.execute("""
                    INSERT INTO direccion
                        (id_jugador, id_municipio, nombre_municipio,
                         estado_residencia,
                         calle, numero_exterior, colonia, codigo_postal)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    id_persona, id_municipio, nombre_municipio,
                    data.get('estado_residencia', '').upper() or None,
                    data.get('calle', '').upper(),
                    data.get('numero_exterior', '') or None,
                    data.get('colonia', '').upper(),
                    data.get('codigo_postal', ''),
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
                    data.get('codigo_postal', ''),
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
                    data.get('curp_tutor', '').upper() or None,
                ))

        elif tipo == 'entrenador':
            cur.execute("""
                INSERT INTO entrenador (
                    apellido_paterno, apellido_materno, nombres,
                    numero_registro, curp, vigencia,
                    fecha_nacimiento, lugar_nacimiento, nacionalidad,
                    peso, estatura, tipo_sangre,
                    ocupacion, escolaridad, escuela,
                    telefono, celular, correo_electronico,
                    enfermedades_cronicas, medicamentos,
                    club, categoria, rama, ligas_participa,
                    fotografia, cedula, especialidad, firma_base64
                ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """, (
                apellido_paterno, apellido_materno, nombres,
                numero_registro, curp, vigencia or None,
                fecha_nacimiento, lugar_nacimiento, nacionalidad,
                peso, estatura, tipo_sangre,
                ocupacion, escolaridad, escuela,
                telefono, celular, correo,
                enfermedades, medicamentos,
                club, categoria, rama, ligas_participa,
                ruta_foto,
                data.get('cedula') or None,
                data.get('especialidad') or None,
                firma_base64_guardar,
            ))
            id_persona = cur.lastrowid

        elif tipo == 'arbitro':
            cur.execute("""
                INSERT INTO arbitro (
                    apellido_paterno, apellido_materno, nombres,
                    numero_registro, curp, vigencia,
                    fecha_nacimiento, lugar_nacimiento, nacionalidad,
                    peso, estatura, tipo_sangre,
                    ocupacion, escolaridad, escuela,
                    telefono, celular, correo_electronico,
                    enfermedades_cronicas, medicamentos,
                    club, categoria, rama, ligas_participa,
                    fotografia, zona, licencia, firma_base64
                ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """, (
                apellido_paterno, apellido_materno, nombres,
                numero_registro, curp, vigencia or None,
                fecha_nacimiento, lugar_nacimiento, nacionalidad,
                peso, estatura, tipo_sangre,
                ocupacion, escolaridad, escuela,
                telefono, celular, correo,
                enfermedades, medicamentos,
                club, categoria, rama, ligas_participa,
                ruta_foto,
                data.get('zona') or None,
                data.get('licencia') or None,
                firma_base64_guardar,
            ))
            id_persona = cur.lastrowid

        # ── Autorización pendiente ────────────────────────────────
        cur.execute("""
            INSERT INTO autorizacion_pendiente
                (tipo_solicitud, id_referencia, fecha_solicitud, estatus)
            VALUES (%s, %s, NOW(), 'Pendiente')
        """, (tipo, id_persona))

        # ── Notificar a todos los admins ──────────────────────────
        cur.execute("SELECT id_usuario FROM usuario WHERE activo = 1")
        admins = cur.fetchall()
        nombre_reg = f"{apellido_paterno} {nombres}".strip()
        for admin in admins:
            notificar(cur, admin['id_usuario'],
                      f"Nueva solicitud de registro externo: {nombre_reg} ({tipo}). "
                      f"Pendiente de autorización.")

        mysql.connection.commit()
        cur.close()
        session.pop('ext_nombre', None)
        session.pop('ext_email', None)
        return jsonify({'ok': True, 'mensaje': f'{tipo.capitalize()} registrado correctamente.'})

    except Exception as e:
        mysql.connection.rollback()
        cur.close()
        return jsonify({'ok': False, 'mensaje': str(e)}), 500

# ── Ruta pública para obtener el siguiente número de registro (formulario externo) ──
@auth.route("/registro-externo/siguiente_registro")
def siguienteRegistroExterno():
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
    
@auth.route("/registroExitoso")
def registroExitoso():
    return render_template("registro/registroExitoso.html")