import os
import psycopg2
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app) 

# --- CONFIGURACIÓN DE CONEXIÓN A LA BASE DE DATOS ---
def conectar_db():
    try:
        conn = psycopg2.connect(
            dbname=os.getenv('DB_NAME'),
            user=os.getenv('DB_USER'),
            password=os.getenv('DB_PASS'),
            host=os.getenv('DB_HOST'),
            port=os.getenv('DB_PORT')
        )
        return conn
    except psycopg2.Error as e:
        print(f"Error al conectar a PostgreSQL: {e}")
        return None

# --- ENDPOINT PARA INICIAR SESIÓN Y CREAR ESTUDIANTE ---
@app.route('/api/iniciar-sesion', methods=['POST'])
def iniciar_sesion():
    datos = request.json
    codigo_institucional = datos.get('codigo')
    email = datos.get('email')

    if not codigo_institucional or not email:
        return jsonify({'error': 'Faltan datos'}), 400

    conn = conectar_db()
    if conn is None:
        return jsonify({'error': 'No se pudo conectar a la base de datos'}), 500
    
    cursor = conn.cursor()
    try:
        # Verificar si el estudiante ya existe
        cursor.execute("SELECT id_estudiante FROM estudiantes WHERE codigo_institucional = %s", (codigo_institucional,))
        estudiante = cursor.fetchone()

        if estudiante:
            id_estudiante = estudiante[0]
        else:
            # Si no existe, lo crea
            cursor.execute(
                "INSERT INTO estudiantes (codigo_institucional, email) VALUES (%s, %s) RETURNING id_estudiante",
                (codigo_institucional, email)
            )
            id_estudiante = cursor.fetchone()[0]
        
        # Crear una nueva sesión de test para el estudiante
        cursor.execute(
            "INSERT INTO sesiones_test (id_estudiante) VALUES (%s) RETURNING id_sesion",
            (id_estudiante,)
        )
        id_sesion = cursor.fetchone()[0]
        
        conn.commit()
        return jsonify({'id_sesion': id_sesion})

    except psycopg2.Error as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()

# --- ENDPOINT PARA GUARDAR LAS RESPUESTAS DEL TEST ---
@app.route('/api/guardar-respuestas', methods=['POST'])
def guardar_respuestas():
    datos = request.json
    id_sesion = datos.get('id_sesion')
    respuestas = datos.get('respuestas')

    if not id_sesion or not respuestas:
        return jsonify({'error': 'Faltan datos'}), 400

    # ---- INICIO DE LA VALIDACIÓN DEL BACKEND ----
    
    # 1. VALIDACIÓN DE NÚMERO DE PREGUNTAS
    # Se asegura de que el test esté completo.
    if len(respuestas) != 60:
        return jsonify({'error': f'Número de respuestas incorrecto. Se esperaban 60 y se recibieron {len(respuestas)}.'}), 400

    conn = conectar_db()
    if conn is None:
        return jsonify({'error': 'No se pudo conectar a la base de datos'}), 500
    
    cursor = conn.cursor()
    try:
        # 2. VALIDACIÓN DE ENVÍOS DUPLICADOS
        # Revisa si esta sesión ya fue marcada como 'finalizado'.
        cursor.execute("SELECT estado FROM sesiones_test WHERE id_sesion = %s", (id_sesion,))
        sesion = cursor.fetchone()
        if sesion and sesion[0] == 'finalizado':
            return jsonify({'error': 'Este test ya ha sido finalizado y no puede ser enviado de nuevo.'}), 409 # 409 Conflict

        # ---- FIN DE LA VALIDACIÓN DEL BACKEND ----

        # Insertar todas las respuestas
        for r in respuestas:
            cursor.execute(
                "INSERT INTO respuestas (id_sesion, id_pregunta, respuesta_seleccionada) VALUES (%s, %s, %s)",
                (id_sesion, r['id_pregunta'], r['respuesta'])
            )
        
        # Actualizar el estado de la sesión a 'finalizado'
        cursor.execute(
            "UPDATE sesiones_test SET estado = 'finalizado' WHERE id_sesion = %s",
            (id_sesion,)
        )
        
        conn.commit()
        return jsonify({'mensaje': 'Respuestas guardadas exitosamente'})

    except psycopg2.Error as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()

if __name__ == '__main__':
    app.run(debug=True)