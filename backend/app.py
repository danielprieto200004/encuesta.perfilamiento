import os
from flask import Flask, request, jsonify
from flask_cors import CORS
import psycopg2

app = Flask(__name__)
CORS(app)

# --- CONFIGURACIÓN PARA LEER LOS DATOS DESDE RENDER ---
db_name = os.getenv('DB_NAME')
db_user = os.getenv('DB_USER')
db_pass = os.getenv('DB_PASS')
db_host = os.getenv('DB_HOST')
db_port = os.getenv('DB_PORT')

# Cadena de conexión
def conectar_db():
    try:
        conn = psycopg2.connect(
            dbname=db_name,
            user=db_user,
            password=db_pass,
            host=db_host,
            port=db_port
        )
        conn.autocommit = False
        return conn
    except psycopg2.Error as e:
        print(f"Error al conectar a PostgreSQL: {e}")
        return None

# --- RUTAS DE LA API ---
@app.route('/api/iniciar-sesion', methods=['POST'])
def iniciar_sesion():
    # ... (el resto de tu función no cambia)
    datos = request.get_json()
    codigo_institucional = datos['codigo_institucional']
    email = datos['email']

    conn = conectar_db()
    if conn is None: return jsonify({"error": "No se pudo conectar a la base de datos"}), 500

    cursor = conn.cursor()
    try:
        cursor.execute("SELECT id_estudiante FROM estudiantes WHERE codigo_institucional = %s", (codigo_institucional,))
        resultado = cursor.fetchone()
        id_estudiante = None
        if resultado:
            id_estudiante = resultado[0]
        else:
            cursor.execute("INSERT INTO estudiantes (codigo_institucional, email) VALUES (%s, %s) RETURNING id_estudiante", (codigo_institucional, email))
            id_estudiante = cursor.fetchone()[0]
        cursor.execute("INSERT INTO sesiones_test (id_estudiante) VALUES (%s) RETURNING id_sesion", (id_estudiante,))
        id_sesion = cursor.fetchone()[0]
        conn.commit()
        return jsonify({"id_sesion": id_sesion})
    except psycopg2.Error as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        cursor.close()
        conn.close()


@app.route('/api/guardar-respuestas', methods=['POST'])
def guardar_respuestas():
    # ... (el resto de tu función no cambia)
    datos = request.get_json()
    id_sesion = datos['id_sesion']
    respuestas = datos['respuestas']

    conn = conectar_db()
    if conn is None: return jsonify({"error": "No se pudo conectar a la base de datos"}), 500

    cursor = conn.cursor()
    try:
        query = "INSERT INTO respuestas (id_sesion, id_pregunta, respuesta_seleccionada) VALUES (%s, %s, %s)"
        datos_respuestas = [(id_sesion, r['id_pregunta'], r['respuesta']) for r in respuestas]
        cursor.executemany(query, datos_respuestas)
        cursor.execute("UPDATE sesiones_test SET estado = 'finalizado' WHERE id_sesion = %s", (id_sesion,))
        conn.commit()
        return jsonify({"mensaje": "Respuestas guardadas exitosamente"})
    except psycopg2.Error as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        cursor.close()
        conn.close()

# Ya NO se llama a inicializar_db() aquí
# El bloque if __name__ == '__main__' se puede quitar, Gunicorn no lo usa.
