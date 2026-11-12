"""
Módulo de USUARIOS para la API de Hojas de Vida (SENA)

Rutas:
  GET    /                      -> Página principal (lista de usuarios + formulario de registro)
  GET    /usuarios              -> Lista de usuarios (JSON)
  GET    /usuarios/<id>         -> Un usuario (JSON)
  POST   /usuarios              -> Registrar usuario (no deja correos repetidos)
  POST   /login                 -> Iniciar sesión con correo y contraseña
"""
from datetime import date, datetime

import mysql.connector
from flask import Blueprint, jsonify, render_template, request
from werkzeug.security import check_password_hash, generate_password_hash

from database import conectar_bd

usuarios_bp = Blueprint("usuarios", __name__)


@usuarios_bp.record_once
def _configurar(state):
    # Para que las tildes y la ñ se vean bien en Postman (y no como á)
    state.app.config["JSON_AS_ASCII"] = False
    if hasattr(state.app, "json"):
        state.app.json.ensure_ascii = False

ROLES = ("Administrador", "Instructor", "Aprendiz")
ESTADOS = ("Activo", "Inactivo")

# Columnas que se devuelven (NUNCA se devuelve el password)
COLUMNAS = "id_usuario, nombre_usuario, correo, rol, estado, fecha_nacimiento, fecha_creacion"


def _formatear(usuario):
    """Convierte las fechas a texto (AAAA-MM-DD) para que se vean bien en el JSON."""
    for campo, valor in usuario.items():
        if isinstance(valor, (date, datetime)):
            usuario[campo] = valor.isoformat(sep=" ") if isinstance(valor, datetime) else valor.isoformat()
    return usuario


def _obtener_usuarios():
    conexion = conectar_bd()
    cursor = conexion.cursor(dictionary=True)
    cursor.execute(f"SELECT {COLUMNAS} FROM usuarios ORDER BY id_usuario DESC")
    usuarios = [_formatear(u) for u in cursor.fetchall()]
    cursor.close()
    conexion.close()
    return usuarios



@usuarios_bp.route("/")
def inicio():
    return render_template("index.html", usuarios=_obtener_usuarios())


@usuarios_bp.route("/usuarios", methods=["GET"])
def listar_usuarios():
    return jsonify(_obtener_usuarios()), 200


@usuarios_bp.route("/usuarios/<int:id_usuario>", methods=["GET"])
def ver_usuario(id_usuario):
    conexion = conectar_bd()
    cursor = conexion.cursor(dictionary=True)
    cursor.execute(f"SELECT {COLUMNAS} FROM usuarios WHERE id_usuario = %s", (id_usuario,))
    usuario = cursor.fetchone()
    cursor.close()
    conexion.close()

    if usuario is None:
        return jsonify({"error": "Usuario no encontrado"}), 404
    return jsonify(_formatear(usuario)), 200



@usuarios_bp.route("/usuarios", methods=["POST"])
def crear_usuario():
    datos = request.get_json(silent=True) or request.form.to_dict()

    nombre_usuario = (datos.get("nombre_usuario") or "").strip()
    correo = (datos.get("correo") or "").strip().lower()   # en minúscula para que "Ana@x.com" y "ana@x.com" cuenten como el mismo
    password = datos.get("password") or ""
    fecha_nacimiento = (datos.get("fecha_nacimiento") or "").strip()
    rol = datos.get("rol") or "Aprendiz"
    estado = datos.get("estado") or "Activo"

    # 1. Validar que vengan los datos obligatorios
    faltantes = [campo for campo, valor in {
        "nombre_usuario": nombre_usuario,
        "correo": correo,
        "password": password,
        "fecha_nacimiento": fecha_nacimiento,
    }.items() if not valor]
    if faltantes:
        return jsonify({"error": "Faltan campos obligatorios", "campos": faltantes}), 400

    if "@" not in correo or "." not in correo.split("@")[-1]:
        return jsonify({"error": "El correo no es válido"}), 400
    if len(password) < 6:
        return jsonify({"error": "La contraseña debe tener mínimo 6 caracteres"}), 400
    if rol not in ROLES:
        return jsonify({"error": f"Rol no válido. Usa uno de: {', '.join(ROLES)}"}), 400
    if estado not in ESTADOS:
        return jsonify({"error": f"Estado no válido. Usa uno de: {', '.join(ESTADOS)}"}), 400
    try:
        datetime.strptime(fecha_nacimiento, "%Y-%m-%d")
    except ValueError:
        return jsonify({"error": "fecha_nacimiento debe tener el formato AAAA-MM-DD"}), 400

    conexion = conectar_bd()
    cursor = conexion.cursor(dictionary=True)
    try:
        # 2. Revisar que el correo NO exista
        cursor.execute("SELECT id_usuario FROM usuarios WHERE correo = %s", (correo,))
        if cursor.fetchone():
            return jsonify({"error": "Ese correo ya está registrado"}), 409

        # 3. Revisar que el nombre de usuario NO exista
        cursor.execute("SELECT id_usuario FROM usuarios WHERE nombre_usuario = %s", (nombre_usuario,))
        if cursor.fetchone():
            return jsonify({"error": "Ese nombre de usuario ya existe"}), 409

        # 4. Guardar con la contraseña encriptada
        cursor.execute(
            """INSERT INTO usuarios (nombre_usuario, correo, password, rol, estado, fecha_nacimiento)
               VALUES (%s, %s, %s, %s, %s, %s)""",
            (nombre_usuario, correo, generate_password_hash(password), rol, estado, fecha_nacimiento),
        )
        conexion.commit()
        nuevo_id = cursor.lastrowid

    except mysql.connector.IntegrityError:
        # Respaldo: si dos registros llegan al mismo tiempo, el UNIQUE de la BD lo frena
        conexion.rollback()
        return jsonify({"error": "El correo o el nombre de usuario ya están registrados"}), 409
    finally:
        cursor.close()
        conexion.close()

    return jsonify({
        "mensaje": "Usuario registrado correctamente",
        "usuario": {
            "id_usuario": nuevo_id,
            "nombre_usuario": nombre_usuario,
            "correo": correo,
            "rol": rol,
            "estado": estado,
            "fecha_nacimiento": fecha_nacimiento,
        },
    }), 201


# ---------------------------------------------------------------------
# LOGIN
# ---------------------------------------------------------------------
@usuarios_bp.route("/login", methods=["POST"])
def login():
    datos = request.get_json(silent=True) or request.form.to_dict()
    correo = (datos.get("correo") or "").strip().lower()
    password = datos.get("password") or ""

    if not correo or not password:
        return jsonify({"error": "Debes enviar correo y password"}), 400

    conexion = conectar_bd()
    cursor = conexion.cursor(dictionary=True)
    cursor.execute(f"SELECT {COLUMNAS}, password FROM usuarios WHERE correo = %s", (correo,))
    usuario = cursor.fetchone()
    cursor.close()
    conexion.close()

    if usuario is None or not _password_correcto(usuario["password"], password):
        return jsonify({"error": "Correo o contraseña incorrectos"}), 401
    if usuario["estado"] != "Activo":
        return jsonify({"error": "El usuario está inactivo"}), 403

    usuario.pop("password")
    return jsonify({"mensaje": "Inicio de sesión exitoso", "usuario": _formatear(usuario)}), 200


def _password_correcto(hash_guardado, password):
    # Usuarios de prueba creados en el .sql con SHA2 (64 caracteres hexadecimales, sin formato de werkzeug)
    if "$" not in hash_guardado:
        import hashlib
        return hashlib.sha256(password.encode()).hexdigest() == hash_guardado
    return check_password_hash(hash_guardado, password)
