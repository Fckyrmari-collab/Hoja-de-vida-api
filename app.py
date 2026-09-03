from flask import Flask
from database import conectar_bd

app = Flask(__name__)


@app.route("/")
def inicio():
    return "Api hoja de vida funcionando"


@app.route("/conectar_bd/")
def conectarbasededatos():
    conexion = conectar_bd()
    if conexion.is_connected():
        conexion.close()
        return {"mensaje": "conexion ok"}
    return {"mensaje": "no se pudo conectar"}


@app.route("/api/hojas-vida/<int:id>")
def obtener_hojavidaid(id):
    conexion = conectar_bd()
    cursor = conexion.cursor(dictionary=True)
    cursor.execute("SELECT * FROM hojas_vida WHERE id = %s", (id,))
    resultado = cursor.fetchone()
    cursor.close()
    conexion.close()

    if resultado:
        return resultado
    return {"mensaje": "hoja de vida no encontrada"}, 404



@app.route("/api/hojas-vida")
def obtener_hojasvida():
    conexion = conectar_bd()
    cursor = conexion.cursor(dictionary=True)
    cursor.execute("SELECT * FROM hojas_vida")
    hojas_vida = cursor.fetchall()
    cursor.close()
    conexion.close()

    return {"hojas_vida": hojas_vida}


if __name__ == "__main__":
    app.run(debug=True)