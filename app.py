import os
from flask import Flask, request, jsonify
from flask_cors import CORS
import psycopg2 # Cambiado a psycopg2

app = Flask(__name__)
CORS(app)

# --- CONFIGURACIÓN PARA LEER LOS DATOS DESDE RENDER ---
# Render inyecta estas variables de entorno al crear la DB
db_name = os.getenv('DB_NAME')
db_user = os.getenv('DB_USER')
db_pass = os.getenv('DB_PASS')
db_host = os.getenv('DB_HOST')
db_port = os.getenv('DB_PORT')

# Cadena de conexión adaptada para PostgreSQL
def conectar_db():
    try:
        conn = psycopg2.connect(
            dbname=db_name,
            user=db_user,
            password=db_pass,
            host=db_host,
            port=db_port
        )
        conn.autocommit = False # Mantenemos el manejo manual de transacciones
        return conn
    except psycopg2.Error as e:
        print(f"Error al conectar a PostgreSQL: {e}")
        return None

# --- FUNCIÓN PARA CREAR LAS TABLAS SI NO EXISTEN ---
# Es necesario adaptar la sintaxis SQL al dialecto de PostgreSQL
def inicializar_db():
    conn = conectar_db()
    if conn is None:
        print("No se pudo conectar a la DB para la inicialización.")
        return

    cursor = conn.cursor()
    try:
        # PostgreSQL usa information_schema para revisar si existen las tablas
        cursor.execute("SELECT 1 FROM information_schema.tables WHERE table_name = 'estudiantes'")
        if cursor.fetchone() is None:
            print("Tablas no encontradas. Creando estructura de base de datos...")
            # Aquí debes pegar el código de tu archivo base.sql adaptado para PostgreSQL
            # Ver el paso 2 para la sintaxis correcta.

            # Por ahora, solo adaptaremos las sentencias a continuación
            cursor.execute("""
            CREATE TABLE estudiantes (
              id_estudiante SERIAL PRIMARY KEY,
              codigo_institucional VARCHAR(45) NOT NULL UNIQUE,
              email VARCHAR(255) NOT NULL UNIQUE,
              fecha_registro TIMESTAMP NOT NULL DEFAULT NOW()
            );
            """)
            cursor.execute("""
            CREATE TABLE sesiones_test (
              id_sesion SERIAL PRIMARY KEY,
              id_estudiante INT NOT NULL REFERENCES estudiantes(id_estudiante) ON DELETE CASCADE,
              fecha_inicio TIMESTAMP NOT NULL DEFAULT NOW(),
              estado VARCHAR(15) NOT NULL DEFAULT 'iniciado'
            );
            """)
            cursor.execute("""
            CREATE TABLE respuestas (
              id_respuesta SERIAL PRIMARY KEY,
              id_sesion INT NOT NULL REFERENCES sesiones_test(id_sesion) ON DELETE CASCADE,
              id_pregunta VARCHAR(10) NOT NULL,
              respuesta_seleccionada CHAR(1) NOT NULL,
              fecha_respuesta TIMESTAMP NOT NULL DEFAULT NOW()
            );
            """)
            conn.commit()
            print("Tablas creadas exitosamente.")
        else:
            print("Las tablas ya existen. No se necesita inicialización.")
    except psycopg2.Error as e:
        print(f"Error al inicializar la base de datos: {e}")
    finally:
        cursor.close()
        conn.close()

# --- RUTAS DE LA API (SIN CAMBIOS, SOLO LOS DETALLES DE CONEXIÓN INTERNOS) ---
@app.route('/api/iniciar-sesion', methods=['POST'])
def iniciar_sesion():
    datos = request.get_json()
    codigo_institucional = datos['codigo_institucional']
    email = datos['email']

    conn = conectar_db()
    if conn is None: return jsonify({"error": "No se pudo conectar a la base de datos"}), 500

    cursor = conn.cursor()
    try:
        # Buscar estudiante por codigo
        cursor.execute("SELECT id_estudiante FROM estudiantes WHERE codigo_institucional = %s", (codigo_institucional,))
        resultado = cursor.fetchone()

        id_estudiante = None
        if resultado:
            id_estudiante = resultado[0]
        else:
            # Insertar nuevo estudiante
            cursor.execute("INSERT INTO estudiantes (codigo_institucional, email) VALUES (%s, %s) RETURNING id_estudiante", (codigo_institucional, email))
            id_estudiante = cursor.fetchone()[0]

        # Iniciar nueva sesion
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

# Se llama a la inicialización antes de arrancar el servidor
# Por favor, asegúrate de que esta línea esté al final del archivo
inicializar_db()

if __name__ == '__main__':
    app.run(debug=True, port=5000)