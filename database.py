import mysql.connector


def conectar_bd():
    conexion = mysql.connector.connect(
        host="localhost",
        user="root",
        password="",   # pon aquí tu contraseña real de MySQL
        database="hojadevida2026"
    )
    return conexion