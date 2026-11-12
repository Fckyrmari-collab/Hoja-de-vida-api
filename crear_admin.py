from flask import Flask, request
from database import conectar_bd
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
from flask_jwt_extended import create_access_token
from dotenv import load_dotenv
import os
from getpass import getpass


def crear_administrador():
    nombre = input("Nombre del reclutador: ").strip()
    correo = input("Correo electrónico: ").strip().lower()
    password = getpass("Contraseña: ")   # no se ve mientras escribes (es normal)

    if not nombre or not correo or len(password) < 8:
        print("Verifica los datos. La clave requiere mínimo 8 caracteres")
        return

    conexion = conectar_bd()
    cursor = conexion.cursor()

    try:
        # CAMBIO 1: la llave primaria se llama id_usuario (no id)
        cursor.execute(
            "SELECT id_usuario FROM usuarios WHERE correo = %s",
            (correo,)
        )
        if cursor.fetchone():
            print("Este correo ya está registrado")
            return

        password_hash = generate_password_hash(password)

        # CAMBIO 2: la columna es nombre_usuario (no nombre)
        # CAMBIO 3: rol y estado son ENUM -> 'Reclutador' y 'Activo' (no 'reclutador' ni 1)
        sql = """
            INSERT INTO usuarios
            (nombre_usuario, correo, password, rol, estado)
            VALUES (%s, %s, %s, 'Reclutador', 'Activo')
        """
        cursor.execute(sql, (nombre, correo, password_hash))
        conexion.commit()
        print("Reclutador creado correctamente")

    except Exception as error:
        conexion.rollback()
        print("Error:", error)
    finally:
        cursor.close()
        conexion.close()


if __name__ == "__main__":
    crear_administrador()