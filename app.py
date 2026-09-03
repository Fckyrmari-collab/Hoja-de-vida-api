import re
from flask import Flask,request,jsonify
from database import conectar_bd
app = Flask(__name__)

# Patrón simple para validar formato de correo (algo@algo.algo)
PATRON_CORREO = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"

def validar_registro(datos):
    """Revisa que vengan los campos obligatorios y con formato correcto.
    Devuelve una lista de errores (vacía si todo está bien)."""
    errores = []
    campos_obligatorios = ["nombre","edad","ciudad","correo","programa","ficha","jornada"]

    if not datos:
        return ["No se recibió ningún dato en formato JSON"]

    for campo in campos_obligatorios:
        if campo not in datos or datos[campo] in (None,""):
            errores.append(f"El campo '{campo}' es obligatorio")

    if "correo" in datos and datos["correo"]:
        if not re.match(PATRON_CORREO,datos["correo"]):
            errores.append("El correo no tiene un formato válido")

    if "edad" in datos and datos["edad"] not in (None,""):
        try:
            edad = int(datos["edad"])
            if edad < 14 or edad > 100:
                errores.append("La edad debe estar entre 14 y 100 años")
        except (ValueError,TypeError):
            errores.append("La edad debe ser un número")

    if "ficha" in datos and datos["ficha"] not in (None,""):
        try:
            int(datos["ficha"])
        except (ValueError,TypeError):
            errores.append("La ficha debe ser un número")

    jornadas_validas = ["Mañana","Tarde","Noche","Mixta"]
    if "jornada" in datos and datos["jornada"] not in (None,"") and datos["jornada"] not in jornadas_validas:
        errores.append(f"La jornada debe ser una de: {', '.join(jornadas_validas)}")

    return errores



@app.route("/probar")
def probar_data():
    conec = conectar_bd()
    if conec.is_connected():
        conec.close()
    return{
        "mensaje":"conexion ok"
    }

@app.route("/api/registrohv",methods=["POST"])
def registrohvida():
    datos = request.json

    errores = validar_registro(datos)
    if errores:
        return jsonify({
            "mensaje":"Datos inválidos",
            "errores":errores
        }),400

    conec = conectar_bd()
    cursor = conec.cursor(dictionary=True)
    buscar="""SELECT id_aprendiz,nombre FROM aprendices WHERE correo = %s"""

    cursor.execute(buscar,(datos["correo"],))
    usu = cursor.fetchone()
    if usu:
            cursor.close()
            conec.close()
            return{
            "mensaje":"el usuario ya existe"
            }

    sql = """INSERT INTO aprendices(nombre,edad,ciudad,correo,foto,programa,ficha,jornada)VALUES(%s,%s,%s,%s,%s,%s,%s,%s)"""
    valor = (datos["nombre"],
            datos["edad"],
            datos["ciudad"],
            datos["correo"],
            datos.get("foto"),
            datos["programa"],
            datos["ficha"],
            datos["jornada"])

    cursor.execute(sql,valor)
    conec.commit()

    #manejo del id de la hoja de vida 
    id_generado = cursor.lastrowid
    cursor.close()
    conec.close()
    return{
        "mensaje":"Hoja de vida creada","id":id_generado
    }



@app.route("/")
def inicio():
    return"Api hoja de vida funcionando"

@app.route("/api/hojas-vida/<int:id>")
def obtener_hojasvidaid(id):
    conec = conectar_bd()
    cursor = conec.cursor(dictionary=True)

    sql = """SELECT id_aprendiz,nombre,edad,ciudad,correo,foto,programa,ficha,jornada
             FROM aprendices WHERE id_aprendiz = %s"""
    cursor.execute(sql,(id,))
    aprendiz = cursor.fetchone()

    cursor.close()
    conec.close()

    if not aprendiz:
        return jsonify({
            "mensaje":"Hoja de vida no encontrada"
        }),404

    return jsonify({
        "mensaje":"Hoja de vida encontrada",
        "datos":aprendiz
    })

@app.route("/api/hojas-vida")
def obtener_hojasvida():
    conec = conectar_bd()
    cursor = conec.cursor(dictionary=True)

    sql = """SELECT id_aprendiz,nombre,edad,ciudad,correo,foto,programa,ficha,jornada
             FROM aprendices"""
    cursor.execute(sql)
    hojas_vida = cursor.fetchall()

    cursor.close()
    conec.close()

    return jsonify(hojas_vida)

if __name__== "__main__":
    app.run(debug=True)