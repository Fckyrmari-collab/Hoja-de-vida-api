from datetime import date, datetime

import mysql.connector
from flask import Flask, request, render_template
from database import conectar_bd
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash


app = Flask(__name__)
CORS(app)
app.json.ensure_ascii = False   # para que las tildes y la ñ se vean bien en Postman


@app.route("/probar")
def probar_data():
    conec = conectar_bd()
    if conec.is_connected():
        conec.close()
    return {"mensaje": "conexion ok"}



# =========================================================
# USUARIOS (tabla: usuarios)
# =========================================================

# Columnas que se devuelven (NUNCA se devuelve el password)
COLUMNAS_USUARIO = "id_usuario, nombre_usuario, correo, rol, estado, fecha_nacimiento, fecha_creacion"
ROLES = ("Administrador", "Instructor", "Aprendiz")


def formatear_usuario(usuario):
    """Convierte las fechas a texto (AAAA-MM-DD) para que se vean bien en el JSON."""
    for campo, valor in usuario.items():
        if isinstance(valor, datetime):
            usuario[campo] = valor.strftime("%Y-%m-%d %H:%M:%S")
        elif isinstance(valor, date):
            usuario[campo] = valor.isoformat()
    return usuario


def listar_usuarios_bd():
    conec = conectar_bd()
    cursor = conec.cursor(dictionary=True)
    cursor.execute(f"SELECT {COLUMNAS_USUARIO} FROM usuarios ORDER BY id_usuario DESC")
    usuarios = [formatear_usuario(u) for u in cursor.fetchall()]
    cursor.close()
    conec.close()
    return usuarios


@app.route("/api/registro-usuario",methods=["POST"])
def registro_usuario():
    datos = request.get_json(silent=True) or {}

    nombre_usuario = (datos.get("nombre_usuario") or "").strip()
    correo = (datos.get("correo") or "").strip().lower()   # en minúscula: "Ana@x.com" y "ana@x.com" son el mismo
    password = datos.get("password") or ""
    fecha_nacimiento = (datos.get("fecha_nacimiento") or "").strip()
    rol = datos.get("rol") or "Aprendiz"

    # 1. Validar datos
    faltantes = [campo for campo, valor in {
        "nombre_usuario": nombre_usuario,
        "correo": correo,
        "password": password,
        "fecha_nacimiento": fecha_nacimiento,
    }.items() if not valor]
    if faltantes:
        return {"error": "Faltan campos obligatorios", "campos": faltantes}, 400
    if "@" not in correo or "." not in correo.split("@")[-1]:
        return {"error": "El correo no es válido"}, 400
    if len(password) < 6:
        return {"error": "La contraseña debe tener mínimo 6 caracteres"}, 400
    if rol not in ROLES:
        return {"error": f"Rol no válido. Usa uno de: {', '.join(ROLES)}"}, 400
    try:
        datetime.strptime(fecha_nacimiento, "%Y-%m-%d")
    except ValueError:
        return {"error": "fecha_nacimiento debe tener el formato AAAA-MM-DD"}, 400

    conec = conectar_bd()
    cursor = conec.cursor(dictionary=True)
    try:
        # 2. Revisar que el correo NO exista
        cursor.execute("SELECT id_usuario FROM usuarios WHERE correo = %s", (correo,))
        if cursor.fetchone():
            return {"error": "Ese correo ya está registrado"}, 409

        # 3. Revisar que el nombre de usuario NO exista
        cursor.execute("SELECT id_usuario FROM usuarios WHERE nombre_usuario = %s", (nombre_usuario,))
        if cursor.fetchone():
            return {"error": "Ese nombre de usuario ya existe"}, 409

        # 4. Guardar con la contraseña encriptada
        sql = """INSERT INTO usuarios(nombre_usuario, correo, password, rol, fecha_nacimiento)
                 VALUES(%s, %s, %s, %s, %s)"""
        cursor.execute(sql, (nombre_usuario, correo, generate_password_hash(password), rol, fecha_nacimiento))
        conec.commit()
        id_generado = cursor.lastrowid

    except mysql.connector.IntegrityError:
        # Respaldo: el UNIQUE de la base de datos tampoco deja repetidos
        conec.rollback()
        return {"error": "El correo o el nombre de usuario ya están registrados"}, 409
    finally:
        cursor.close()
        conec.close()

    return {
        "mensaje": "Usuario registrado correctamente",
        "usuario": {
            "id_usuario": id_generado,
            "nombre_usuario": nombre_usuario,
            "correo": correo,
            "rol": rol,
            "estado": "Activo",
            "fecha_nacimiento": fecha_nacimiento,
        },
    }, 201

@app.route("/api/login",methods=["POST"])
def login ():
    datos = request.get_json(silent=True) or {}
    correo = (datos.get("correo") or "").strip().lower()
    password = datos.get("password") or ""

    if not correo or not password:
        return {"error": "Debes enviar correo y password"}, 400

    conec = conectar_bd()
    cursor = conec.cursor(dictionary=True)
    cursor.execute(f"SELECT {COLUMNAS_USUARIO}, password FROM usuarios WHERE correo = %s", (correo,))
    usuario = cursor.fetchone()
    cursor.close()
    conec.close()

    if usuario is None or not password_correcto(usuario["password"], password):
        return {"error": "Correo o contraseña incorrectos"}, 401
    if usuario["estado"] != "Activo":
        return {"error": "El usuario está inactivo"}, 403

    usuario.pop("password")
    return {"mensaje": "Inicio de sesión exitoso", "usuario": formatear_usuario(usuario)}, 200


def password_correcto(hash_guardado, password):
    # Los usuarios de prueba del .sql se crearon con SHA2 (no tienen el formato de werkzeug)
    if "$" not in hash_guardado:
        import hashlib
        return hashlib.sha256(password.encode()).hexdigest() == hash_guardado
    return check_password_hash(hash_guardado, password)


@app.route("/api/usuarios", methods=["GET"])
def listar_usuarios():
    return {"usuarios": listar_usuarios_bd()}


@app.route("/api/usuarios/<int:id_usuario>", methods=["GET"])
def obtener_usuario(id_usuario):
    conec = conectar_bd()
    cursor = conec.cursor(dictionary=True)
    cursor.execute(f"SELECT {COLUMNAS_USUARIO} FROM usuarios WHERE id_usuario = %s", (id_usuario,))
    usuario = cursor.fetchone()
    cursor.close()
    conec.close()
    if not usuario:
        return {"mensaje": "Usuario no encontrado"}, 404
    return formatear_usuario(usuario)


# APRENDICES (HOJAS DE VIDA)


@app.route("/api/registrohv", methods=["POST"])
def registrohvida():
    conec = conectar_bd()
    cursor = conec.cursor(dictionary=True)
    datos = request.json

    buscar = "SELECT id_aprendiz, nombre FROM aprendices WHERE correo = %s"
    cursor.execute(buscar, (datos["correo"],))
    usu = cursor.fetchone()

    if usu:
        cursor.close()
        conec.close()
        return {"mensaje": "el usuario ya existe"}, 400

    # id_usuario: viene si llenó la hoja de vida con sesión iniciada; si es visualizador llega null
    id_usuario = datos.get("id_usuario")

    if id_usuario:
        # Un usuario solo puede tener UNA hoja de vida
        cursor.execute("SELECT id_aprendiz FROM aprendices WHERE id_usuario = %s", (id_usuario,))
        if cursor.fetchone():
            cursor.close()
            conec.close()
            return {"mensaje": "este usuario ya tiene una hoja de vida registrada"}, 400

    sql = """INSERT INTO aprendices(nombre, edad, ciudad, correo, foto, programa, ficha, jornada, id_usuario)
             VALUES(%s, %s, %s, %s, %s, %s, %s, %s, %s)"""
    valor = (
        datos["nombre"],
        datos["edad"],
        datos["ciudad"],
        datos["correo"],
        datos.get("foto"),
        datos["programa"],
        datos["ficha"],
        datos.get("jornada", "Mañana"),
        id_usuario
    )

    try:
        cursor.execute(sql, valor)
        conec.commit()
        id_generado = cursor.lastrowid
    except mysql.connector.IntegrityError:
        conec.rollback()
        return {"mensaje": "el id_usuario no existe o ya tiene hoja de vida"}, 400
    finally:
        cursor.close()
        conec.close()

    return {"mensaje": "Hoja de vida creada", "id": id_generado}, 201

# INFORMACIÓN ACADÉMICA (tabla: informacion_academica)

@app.route("/api/aprendices/<int:id_aprendiz>/estudios", methods=["GET"])
def listar_estudios(id_aprendiz):
    conec = conectar_bd()
    cursor = conec.cursor(dictionary=True)
    cursor.execute("SELECT * FROM informacion_academica WHERE id_aprendiz = %s", (id_aprendiz,))
    estudio = cursor.fetchone()
    cursor.close()
    conec.close()
    if not estudio:
        return {"mensaje": "Información académica no encontrada"}, 404
    return estudio

@app.route("/api/aprendices/<int:id_aprendiz>/estudios", methods=["POST"])
def registrar_estudio(id_aprendiz):
    conec = conectar_bd()
    cursor = conec.cursor()
    datos = request.json

    sql = """INSERT INTO informacion_academica(id_aprendiz, nivel, titulo, institucion, graduacion) 
             VALUES(%s, %s, %s, %s, %s)"""
    valor = (
        id_aprendiz,
        datos["nivel"],
        datos["titulo"],
        datos["institucion"],
        datos["graduacion"]
    )

    try:
        cursor.execute(sql, valor)
        conec.commit()
        id_generado = cursor.lastrowid
        cursor.close()
        conec.close()
        return {"mensaje": "Estudio registrado", "id": id_generado}, 201
    except Exception as e:
        cursor.close()
        conec.close()
        return {"error": str(e)}, 400

@app.route("/api/estudios/<int:id_academico>", methods=["GET"])
def obtener_estudio(id_academico):
    conec = conectar_bd()
    cursor = conec.cursor(dictionary=True)
    cursor.execute("SELECT * FROM informacion_academica WHERE id_academico = %s", (id_academico,))
    estudio = cursor.fetchone()
    cursor.close()
    conec.close()
    if not estudio:
        return {"mensaje": "Estudio no encontrado"}, 404
    return estudio

@app.route("/api/estudios/<int:id_academico>", methods=["PUT"])
def actualizar_estudio(id_academico):
    conec = conectar_bd()
    cursor = conec.cursor()
    datos = request.json

    sql = """UPDATE informacion_academica 
             SET nivel=%s, titulo=%s, institucion=%s, graduacion=%s 
             WHERE id_academico=%s"""
    valor = (datos["nivel"], datos["titulo"], datos["institucion"], datos["graduacion"], id_academico)

    cursor.execute(sql, valor)
    conec.commit()
    filas = cursor.rowcount
    cursor.close()
    conec.close()
    if filas == 0:
        return {"mensaje": "Estudio no encontrado"}, 404
    return {"mensaje": "Estudio actualizado"}

@app.route("/api/estudios/<int:id_academico>", methods=["DELETE"])
def eliminar_estudio(id_academico):
    conec = conectar_bd()
    cursor = conec.cursor()
    cursor.execute("DELETE FROM informacion_academica WHERE id_academico=%s", (id_academico,))
    conec.commit()
    filas = cursor.rowcount
    cursor.close()
    conec.close()
    if filas == 0:
        return {"mensaje": "Estudio no encontrado"}, 404
    return {"mensaje": "Estudio eliminado"}

# =========================================================
# CURSOS (tabla: cursos)
# Relación 1:N con informacion_academica
# =========================================================

@app.route("/api/estudios/<int:id_academico>/cursos", methods=["GET"])
def listar_cursos(id_academico):
    conec = conectar_bd()
    cursor = conec.cursor(dictionary=True)
    cursor.execute("SELECT * FROM cursos WHERE id_academico = %s", (id_academico,))
    cursos = cursor.fetchall()
    cursor.close()
    conec.close()
    return {"cursos": cursos}

@app.route("/api/estudios/<int:id_academico>/cursos", methods=["POST"])
def registrar_curso(id_academico):
    conec = conectar_bd()
    cursor = conec.cursor()
    datos = request.json

    sql = "INSERT INTO cursos(id_academico, nombre_curso) VALUES(%s, %s)"
    cursor.execute(sql, (id_academico, datos["nombre_curso"]))
    conec.commit()
    id_generado = cursor.lastrowid
    cursor.close()
    conec.close()
    return {"mensaje": "Curso registrado", "id": id_generado}, 201

@app.route("/api/cursos/<int:id_curso>", methods=["GET"])
def obtener_curso(id_curso):
    conec = conectar_bd()
    cursor = conec.cursor(dictionary=True)
    cursor.execute("SELECT * FROM cursos WHERE id_curso = %s", (id_curso,))
    curso = cursor.fetchone()
    cursor.close()
    conec.close()
    if not curso:
        return {"mensaje": "Curso no encontrado"}, 404
    return curso

@app.route("/api/cursos/<int:id_curso>", methods=["PUT"])
def actualizar_curso(id_curso):
    conec = conectar_bd()
    cursor = conec.cursor()
    datos = request.json

    sql = "UPDATE cursos SET nombre_curso=%s WHERE id_curso=%s"
    cursor.execute(sql, (datos["nombre_curso"], id_curso))
    conec.commit()
    filas = cursor.rowcount
    cursor.close()
    conec.close()
    if filas == 0:
        return {"mensaje": "Curso no encontrado"}, 404
    return {"mensaje": "Curso actualizado"}

@app.route("/api/cursos/<int:id_curso>", methods=["DELETE"])
def eliminar_curso(id_curso):
    conec = conectar_bd()
    cursor = conec.cursor()
    cursor.execute("DELETE FROM cursos WHERE id_curso=%s", (id_curso,))
    conec.commit()
    filas = cursor.rowcount
    cursor.close()
    conec.close()
    if filas == 0:
        return {"mensaje": "Curso no encontrado"}, 404
    return {"mensaje": "Curso eliminado"}

# =========================================================
# EXPERIENCIA LABORAL (tabla: experiencias)
# =========================================================

@app.route("/api/aprendices/<int:id_aprendiz>/experiencias", methods=["GET"])
def listar_experiencias(id_aprendiz):
    conec = conectar_bd()
    cursor = conec.cursor(dictionary=True)
    cursor.execute("SELECT * FROM experiencias WHERE id_aprendiz = %s", (id_aprendiz,))
    experiencias = cursor.fetchall()
    cursor.close()
    conec.close()
    return {"experiencias": experiencias}

@app.route("/api/aprendices/<int:id_aprendiz>/experiencias", methods=["POST"])
def registrar_experiencia(id_aprendiz):
    conec = conectar_bd()
    cursor = conec.cursor()
    datos = request.json

    sql = "INSERT INTO experiencias(id_aprendiz, empresa, cargo, tiempo) VALUES(%s, %s, %s, %s)"
    valor = (id_aprendiz, datos["empresa"], datos["cargo"], datos.get("tiempo"))

    cursor.execute(sql, valor)
    conec.commit()
    id_generado = cursor.lastrowid
    cursor.close()
    conec.close()
    return {"mensaje": "Experiencia registrada", "id": id_generado}, 201

@app.route("/api/experiencias/<int:id_experiencia>", methods=["GET"])
def obtener_experiencia(id_experiencia):
    conec = conectar_bd()
    cursor = conec.cursor(dictionary=True)
    cursor.execute("SELECT * FROM experiencias WHERE id_experiencia = %s", (id_experiencia,))
    experiencia = cursor.fetchone()
    cursor.close()
    conec.close()
    if not experiencia:
        return {"mensaje": "Experiencia no encontrada"}, 404
    return experiencia

@app.route("/api/experiencias/<int:id_experiencia>", methods=["PUT"])
def actualizar_experiencia(id_experiencia):
    conec = conectar_bd()
    cursor = conec.cursor()
    datos = request.json

    sql = "UPDATE experiencias SET empresa=%s, cargo=%s, tiempo=%s WHERE id_experiencia=%s"
    valor = (datos["empresa"], datos["cargo"], datos.get("tiempo"), id_experiencia)

    cursor.execute(sql, valor)
    conec.commit()
    filas = cursor.rowcount
    cursor.close()
    conec.close()
    if filas == 0:
        return {"mensaje": "Experiencia no encontrada"}, 404
    return {"mensaje": "Experiencia actualizada"}

@app.route("/api/experiencias/<int:id_experiencia>", methods=["DELETE"])
def eliminar_experiencia(id_experiencia):
    conec = conectar_bd()
    cursor = conec.cursor()
    cursor.execute("DELETE FROM experiencias WHERE id_experiencia=%s", (id_experiencia,))
    conec.commit()
    filas = cursor.rowcount
    cursor.close()
    conec.close()
    if filas == 0:
        return {"mensaje": "Experiencia no encontrada"}, 404
    return {"mensaje": "Experiencia eliminada"}

# =========================================================
# HABILIDADES (tabla: habilidades)
# =========================================================

@app.route("/api/experiencias/<int:id_experiencia>/habilidades", methods=["GET"])
def listar_habilidades(id_experiencia):
    conec = conectar_bd()
    cursor = conec.cursor(dictionary=True)
    cursor.execute("SELECT * FROM habilidades WHERE id_experiencia = %s", (id_experiencia,))
    habilidades = cursor.fetchall()
    cursor.close()
    conec.close()
    return {"habilidades": habilidades}

@app.route("/api/experiencias/<int:id_experiencia>/habilidades", methods=["POST"])
def registrar_habilidad(id_experiencia):
    conec = conectar_bd()
    cursor = conec.cursor()
    datos = request.json

    sql = "INSERT INTO habilidades(id_experiencia, nombre_habilidad) VALUES(%s, %s)"
    cursor.execute(sql, (id_experiencia, datos["nombre_habilidad"]))
    conec.commit()
    id_generado = cursor.lastrowid
    cursor.close()
    conec.close()
    return {"mensaje": "Habilidad registrada", "id": id_generado}, 201

@app.route("/api/habilidades/<int:id_habilidad>", methods=["PUT"])
def actualizar_habilidad(id_habilidad):
    conec = conectar_bd()
    cursor = conec.cursor()
    datos = request.json

    sql = "UPDATE habilidades SET nombre_habilidad=%s WHERE id_habilidad=%s"
    cursor.execute(sql, (datos["nombre_habilidad"], id_habilidad))
    conec.commit()
    filas = cursor.rowcount
    cursor.close()
    conec.close()
    if filas == 0:
        return {"mensaje": "Habilidad no encontrada"}, 404
    return {"mensaje": "Habilidad actualizada"}

@app.route("/api/habilidades/<int:id_habilidad>", methods=["DELETE"])
def eliminar_habilidad(id_habilidad):
    conec = conectar_bd()
    cursor = conec.cursor()
    cursor.execute("DELETE FROM habilidades WHERE id_habilidad=%s", (id_habilidad,))
    conec.commit()
    filas = cursor.rowcount
    cursor.close()
    conec.close()
    if filas == 0:
        return {"mensaje": "Habilidad no encontrada"}, 404
    return {"mensaje": "Habilidad eliminada"}

# =========================================================
# FUNCIONES DE EXPERIENCIA (tabla: funciones)
# =========================================================

@app.route("/api/experiencias/<int:id_experiencia>/funciones", methods=["POST"])
def registrar_funcion(id_experiencia):
    conec = conectar_bd()
    cursor = conec.cursor()
    datos = request.json

    sql = "INSERT INTO funciones(id_experiencia, nombre_funcion) VALUES(%s, %s)"
    cursor.execute(sql, (id_experiencia, datos["nombre_funcion"]))
    conec.commit()
    id_generado = cursor.lastrowid
    cursor.close()
    conec.close()
    return {"mensaje": "Función registrada", "id": id_generado}, 201

# =========================================================
# CONSULTA COMPLETA DE HOJA DE VIDA
# =========================================================

@app.route("/api/aprendices/<int:id_aprendiz>/completo", methods=["GET"])
def hoja_vida_completa(id_aprendiz):
    conec = conectar_bd()
    cursor = conec.cursor(dictionary=True)

    cursor.execute("SELECT * FROM aprendices WHERE id_aprendiz = %s", (id_aprendiz,))
    aprendiz = cursor.fetchone()
    if not aprendiz:
        cursor.close()
        conec.close()
        return {"mensaje": "Aprendiz no encontrado"}, 404

    cursor.execute("SELECT * FROM informacion_academica WHERE id_aprendiz = %s", (id_aprendiz,))
    estudio = cursor.fetchone()

    if estudio:
        cursor.execute("SELECT * FROM cursos WHERE id_academico = %s", (estudio["id_academico"],))
        estudio["cursos"] = cursor.fetchall()

    cursor.execute("SELECT * FROM experiencias WHERE id_aprendiz = %s", (id_aprendiz,))
    experiencias = cursor.fetchall()

    for exp in experiencias:
        cursor.execute("SELECT * FROM habilidades WHERE id_experiencia = %s", (exp["id_experiencia"],))
        exp["habilidades"] = cursor.fetchall()
        
        cursor.execute("SELECT * FROM funciones WHERE id_experiencia = %s", (exp["id_experiencia"],))
        exp["funciones"] = cursor.fetchall()

    cursor.close()
    conec.close()

    aprendiz["informacion_academica"] = estudio
    aprendiz["experiencias"] = experiencias

    return aprendiz

@app.route("/")
def inicio():
    # Página principal: lista de usuarios + formulario de registro (templates/index.html)
    return render_template("index.html", usuarios=listar_usuarios_bd())

if __name__ == '__main__':
    app.run(debug=True, port=5000)