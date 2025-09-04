import os
import psycopg2

# --- CONFIGURACIÓN PARA LEER LOS DATOS DESDE RENDER ---
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
        conn.autocommit = False
        return conn
    except psycopg2.Error as e:
        print(f"Error al conectar a PostgreSQL: {e}")
        return None

# --- FUNCIÓN PARA CREAR LAS TABLAS SI NO EXISTEN ---
def inicializar_db():
    conn = conectar_db()
    if conn is None:
        print("No se pudo conectar a la DB para la inicialización.")
        return

    cursor = conn.cursor()
    print("Conectado a la base de datos para inicializar...")
    try:
        cursor.execute("SELECT 1 FROM information_schema.tables WHERE table_name = 'estudiantes'")
        if cursor.fetchone() is None:
            print("Tablas no encontradas. Creando estructura de base de datos...")
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
        print("Conexión cerrada.")

# --- Se llama a la función para que se ejecute al correr el script ---
if __name__ == '__main__':
    inicializar_db()
