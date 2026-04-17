import sqlite3
import pandas as pd
from datetime import datetime
from contextlib import contextmanager
import os
import psycopg2
from psycopg2.extras import RealDictCursor
from registro_config import obtener_registrador

# Configuración de Motor de Base de Datos
URL_PRODUCCION = os.getenv("DATABASE_URL")  # Mantenemos el nombre del secreto de la nube
RUTA_SQLITE = os.getenv("DATABASE_URL_SQLITE", "nehemias.db")
ES_POSTGRES = URL_PRODUCCION is not None and URL_PRODUCCION.startswith("postgres")

logger = obtener_registrador("base_datos")

@contextmanager
def obtener_conexion():
    """Genera una conexión compatible con SQLite o PostgreSQL según el entorno."""
    if ES_POSTGRES:
        # Corregir URL para SQLAlchemy/Psycopg2 si es necesario
        direccion_db = URL_PRODUCCION.replace("postgres://", "postgresql://", 1)
        conexion = psycopg2.connect(direccion_db, cursor_factory=RealDictCursor)
    else:
        conexion = sqlite3.connect(RUTA_SQLITE)
        conexion.row_factory = sqlite3.Row
        
    try:
        yield conexion
    finally:
        conexion.close()

def traducir_sql(consulta):
    """Traduce sintaxis básica de SQLite a PostgreSQL si es necesario."""
    if not ES_POSTGRES:
        return consulta
    
    # 1. Marcadores de posición: ? -> %s
    consulta = consulta.replace("?", "%s")
    
    # 2. Funciones de fecha (strftime -> TO_CHAR)
    # Reemplazo de Años
    consulta = consulta.replace("strftime('%Y',", "TO_CHAR(")
    # Reemplazo de Meses
    consulta = consulta.replace("strftime('%m',", "TO_CHAR(")
    
    # Ajuste manual de formatos tras el cambio a TO_CHAR
    import re
    # Para años: Detectar TO_CHAR(...) = %s y ponerle 'YYYY'
    # Esta regex es inteligente para capturar el contenido del TO_CHAR
    consulta = re.sub(r"TO_CHAR\(([^,)]+)\)\s*=\s*%s", r"TO_CHAR(\1, 'YYYY') = %s", consulta)
    
    # Para meses: Heurística para detectar comparaciones de mes
    if "strftime('%m'," in consulta or "TO_CHAR(" in consulta:
       consulta = consulta.replace("TO_CHAR(created_at) = %s AND TO_CHAR(created_at) = %s", "TO_CHAR(created_at, 'YYYY') = %s AND TO_CHAR(created_at, 'MM') = %s")
       consulta = consulta.replace("TO_CHAR(a.created_at) = %s AND TO_CHAR(a.created_at) = %s", "TO_CHAR(a.created_at, 'YYYY') = %s AND TO_CHAR(a.created_at, 'MM') = %s")
    
    consulta = consulta.replace("as year", ", 'YYYY') as year")
    consulta = consulta.replace("as mes_num", ", 'MM') as mes_num")

    # 3. Autoincrement y Conflictos
    consulta = consulta.replace("INTEGER PRIMARY KEY AUTOINCREMENT", "SERIAL PRIMARY KEY")
    
    # Manejo de INSERT OR IGNORE -> ON CONFLICT DO NOTHING
    if "INSERT OR IGNORE INTO subregiones" in consulta:
        consulta = "INSERT INTO subregiones (nombre) VALUES (%s) ON CONFLICT (nombre) DO NOTHING"
    elif "INSERT OR IGNORE INTO catalog_eventos" in consulta:
        consulta = "INSERT INTO catalog_eventos (nombre) VALUES (%s) ON CONFLICT (nombre) DO NOTHING"
    
    return consulta

def inicializar_db():
    """Crea la estructura de tablas inicial si no existe."""
    logger.info("Verificando/Inicializando esquema de base de datos...")
    with obtener_conexion() as conexion:
        cursor = conexion.cursor()
        
        # Tabla de Subregiones
        cursor.execute(traducir_sql("""
            CREATE TABLE IF NOT EXISTS subregiones (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT NOT NULL UNIQUE
            )
        """))
        
        # Tabla de Eventos Epidemiológicos
        cursor.execute(traducir_sql("""
            CREATE TABLE IF NOT EXISTS catalog_eventos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT NOT NULL UNIQUE
            )
        """))
        
        # Tabla de Usuarios
        cursor.execute(traducir_sql("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL,
                subregion_id INTEGER,
                evento_id INTEGER,
                is_active INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                created_by INTEGER,
                FOREIGN KEY (subregion_id) REFERENCES subregiones(id),
                FOREIGN KEY (evento_id) REFERENCES catalog_eventos(id)
            )
        """))
        
        # Tabla de Actividades (Lotes)
        cursor.execute(traducir_sql("""
            CREATE TABLE IF NOT EXISTS actividades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                titulo TEXT NOT NULL,
                descripcion TEXT,
                subregion_id INTEGER,
                created_by INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status TEXT DEFAULT 'Activa',
                fecha_toma TIMESTAMP,
                fecha_respuesta TIMESTAMP,
                fecha_asignacion TIMESTAMP,
                fecha_cierre TIMESTAMP,
                respuesta_tecnica TEXT,
                anulacion_motivo TEXT,
                FOREIGN KEY (subregion_id) REFERENCES subregiones(id),
                FOREIGN KEY (created_by) REFERENCES users(id)
            )
        """))
        
        # Tabla de Ajustes (Detalle granular de los lotes)
        cursor.execute(traducir_sql("""
            CREATE TABLE IF NOT EXISTS ajustes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                actividad_id INTEGER,
                cod_pre TEXT,
                cod_sub TEXT,
                cod_eve TEXT,
                nom_eve TEXT,
                fec_not TEXT,
                nom_upgd TEXT,
                nmun_notif TEXT,
                tip_ide_ TEXT,
                num_ide_ TEXT,
                pri_nom_ TEXT,
                seg_nom_ TEXT,
                pri_ape_ TEXT,
                seg_ape_ TEXT,
                SSSA_AJUSTE TEXT,
                RegIniFec TEXT,
                status_ajuste TEXT DEFAULT 'Pendiente',
                resultado_rs TEXT DEFAULT 'Pendiente',
                nota_tecnica TEXT,
                evidencia_rs TEXT,
                validacion_red TEXT DEFAULT 'Pendiente',
                FOREIGN KEY (actividad_id) REFERENCES actividades(id)
            )
        """))
        
        # Tabla de Auditoría (Interna de la DB)
        cursor.execute(traducir_sql("""
            CREATE TABLE IF NOT EXISTS logs_auditoria (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                accion TEXT,
                detalle TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))
        conexion.commit()
    logger.info("Esquema de base de datos verificado con éxito.")

# --- Funciones de Auditoría ---

def registrar_accion_en_tx(cursor, id_usuario, accion, detalle=""):
    cursor.execute(
        traducir_sql("INSERT INTO logs_auditoria (user_id, accion, detalle) VALUES (?, ?, ?)"),
        (id_usuario, accion, detalle)
    )
    logger.info(f"AUDITORIA_DB | Usuario {id_usuario} | Acción: {accion} | Detalles: {detalle}")

def registrar_accion(id_usuario, accion, detalle=""):
    with obtener_conexion() as conexion:
        cursor = conexion.cursor()
        registrar_accion_en_tx(cursor, id_usuario, accion, detalle)
        conexion.commit()

# --- Funciones de Catálogos ---

def obtener_catalogo_eventos():
    with obtener_conexion() as conexion:
        return pd.read_sql_query(traducir_sql("SELECT * FROM catalog_eventos ORDER BY nombre"), conexion)

def obtener_subregiones():
    with obtener_conexion() as conexion:
        return pd.read_sql_query(traducir_sql("SELECT * FROM subregiones ORDER BY nombre"), conexion)

# --- Gestión de Usuarios ---

def obtener_usuarios_por_creador(id_creador, filtro_rol=None):
    with obtener_conexion() as conexion:
        consulta = "SELECT u.*, s.nombre as subregion_nombre FROM users u LEFT JOIN subregiones s ON u.subregion_id = s.id WHERE u.created_by = ?"
        params = [id_creador]
        if filtro_rol:
            consulta += " AND u.role = ?"
            params.append(filtro_rol)
        return pd.read_sql_query(traducir_sql(consulta), conexion, params=params)

def crear_usuario(nombre_usuario, hash_clave, rol, id_subregion=None, id_evento=None, creado_por=None):
    with obtener_conexion() as conexion:
        cursor = conexion.cursor()
        try:
            consulta = "INSERT INTO users (username, password_hash, role, subregion_id, evento_id, created_by) VALUES (?, ?, ?, ?, ?, ?)"
            cursor.execute(
                traducir_sql(consulta),
                (nombre_usuario, hash_clave, rol, id_subregion, id_evento, creado_por)
            )
            registrar_accion_en_tx(cursor, creado_por, "CREAR_USUARIO", f"Usuario target: {nombre_usuario}")
            conexion.commit()
            logger.info(f"Usuario {nombre_usuario} (Rol: {rol}) creado exitosamente por ID {creado_por}")
        except Exception as e:
            conexion.rollback()
            logger.error(f"Falló la creación del usuario {nombre_usuario}: {str(e)}")
            raise e

# --- Operaciones de Actividades (Vigilancia) ---

def obtener_actividades_filtradas(rol_usuario, id_usuario, id_subregion=None, estados=None, ano=None, mes=None):
    with obtener_conexion() as conexion:
        consulta = """
            SELECT a.*, s.nombre as subregion_nombre, u.username as creador_nombre
            FROM actividades a 
            JOIN subregiones s ON a.subregion_id = s.id
            JOIN users u ON a.created_by = u.id
            WHERE 1=1
        """
        params = []
        
        if rol_usuario == 'RS':
            consulta += " AND a.subregion_id = ?"
            params.append(id_subregion)
        elif rol_usuario == 'RED':
            consulta += " AND a.created_by = ?"
            params.append(id_usuario)
            
        if estados:
            marcadores = ", ".join(["?"] * len(estados))
            consulta += f" AND a.status IN ({marcadores})"
            params.extend(estados)
            
        if id_subregion and rol_usuario != 'RS':
            consulta += " AND a.subregion_id = ?"
            params.append(id_subregion)
            
        if ano:
            consulta += " AND strftime('%Y', a.created_at) = ?"
            params.append(str(ano))
        if mes:
            consulta += " AND strftime('%m', a.created_at) = ?"
            params.append(str(mes).zfill(2))
            
        consulta += " ORDER BY a.created_at DESC"
        return pd.read_sql_query(traducir_sql(consulta), conexion, params=params)

def crear_actividad(titulo, descripcion, id_subregion, creado_por):
    with obtener_conexion() as conexion:
        cursor = conexion.cursor()
        try:
            ahora = datetime.now()
            consulta = "INSERT INTO actividades (titulo, descripcion, subregion_id, created_by, fecha_asignacion) VALUES (?, ?, ?, ?, ?)"
            cursor.execute(
                traducir_sql(consulta),
                (titulo, descripcion, id_subregion, creado_por, ahora)
            )
            
            # Obtener ID insertado de forma compatible
            if ES_POSTGRES:
                cursor.execute("SELECT LASTVAL()")
                id_actividad = cursor.fetchone()['id'] if isinstance(cursor.fetchone(), dict) else cursor.fetchone()[0]
                # Re-obtener por si acaso el cursor tiene comportamiento diferente
                cursor.execute("SELECT id FROM actividades ORDER BY id DESC LIMIT 1")
                id_actividad = list(cursor.fetchone().values())[0] if ES_POSTGRES else cursor.lastrowid
            else:
                id_actividad = cursor.lastrowid
                
            registrar_accion_en_tx(cursor, creado_por, "CREAR_ACTIVIDAD", f"Título: {titulo} | ID_Lote: {id_actividad}")
            conexion.commit()
            logger.info(f"Nuevo lote desplegado por {creado_por}: {titulo} (Asignado: {ahora})")
            return id_actividad
        except Exception as e:
            conexion.rollback()
            logger.error(f"Error al crear actividad '{titulo}': {str(e)}")
            raise e

def tomar_actividad(id_actividad, id_usuario):
    with obtener_conexion() as conexion:
        cursor = conexion.cursor()
        try:
            consulta = "UPDATE actividades SET status = 'En Proceso', fecha_toma = ? WHERE id = ? AND status = 'Activa'"
            cursor.execute(
                traducir_sql(consulta),
                (datetime.now(), id_actividad)
            )
            registrar_accion_en_tx(cursor, id_usuario, "TOMA_ACTIVIDAD", f"ID_Lote: {id_actividad}")
            conexion.commit()
            logger.info(f"Lote {id_actividad} tomado exitosamente por usuario {id_usuario}")
        except Exception as e:
            conexion.rollback()
            logger.error(f"Error al tomar lote {id_actividad} por {id_usuario}: {str(e)}")
            raise e

def responder_actividad(id_actividad, respuesta, id_usuario):
    with obtener_conexion() as conexion:
        cursor = conexion.cursor()
        try:
            consulta = "UPDATE actividades SET status = 'En Revisión', respuesta_tecnica = ?, fecha_respuesta = ? WHERE id = ? AND status = 'En Proceso'"
            cursor.execute(
                traducir_sql(consulta),
                (respuesta, datetime.now(), id_actividad)
            )
            registrar_accion_en_tx(cursor, id_usuario, "RESPUESTA_ACTIVIDAD", f"ID_Lote: {id_actividad}")
            conexion.commit()
            logger.info(f"Lote {id_actividad} enviado a revisión por usuario {id_usuario}")
        except Exception as e:
            conexion.rollback()
            logger.error(f"Error al responder lote {id_actividad} por {id_usuario}: {str(e)}")
            raise e

def cerrar_actividad(id_actividad, id_usuario):
    with obtener_conexion() as conexion:
        cursor = conexion.cursor()
        try:
            consulta = "UPDATE actividades SET status = 'Cerrada', fecha_cierre = ? WHERE id = ? AND status = 'En Revisión'"
            cursor.execute(
                traducir_sql(consulta),
                (datetime.now(), id_actividad)
            )
            registrar_accion_en_tx(cursor, id_usuario, "CIERRE_ACTIVIDAD", f"ID_Lote: {id_actividad}")
            conexion.commit()
            logger.info(f"Lote {id_actividad} CERRADO y validado por usuario {id_usuario}")
        except Exception as e:
            conexion.rollback()
            logger.error(f"Error al cerrar lote {id_actividad} por {id_usuario}: {str(e)}")
            raise e

def anular_actividad(id_actividad, motivo, id_usuario):
    with obtener_conexion() as conexion:
        cursor = conexion.cursor()
        try:
            consulta = "UPDATE actividades SET status = 'Anulada', anulacion_motivo = ? WHERE id = ?"
            cursor.execute(
                traducir_sql(consulta),
                (motivo, id_actividad)
            )
            registrar_accion_en_tx(cursor, id_usuario, "ANULACION_ACTIVIDAD", f"ID_Lote: {id_actividad}")
            conexion.commit()
            logger.info(f"Lote {id_actividad} ANULADO por usuario {id_usuario}. Motivo: {motivo}")
        except Exception as e:
            conexion.rollback()
            logger.error(f"Error al anular lote {id_actividad} por {id_usuario}: {str(e)}")
            raise e

# --- Gestión Granular (Ajustes) ---

def guardar_ajustes_lote(id_actividad, df_ajustes):
    with obtener_conexion() as conexion:
        cursor = conexion.cursor()
        try:
            # Normalizar nombres de columnas para búsqueda flexible
            columnas_originales = {c.lower().strip(): c for c in df_ajustes.columns}
            
            # Definir mapa de columnas (Interno -> Posibles nombres en Excel)
            mapa_excel = {
                'cod_pre': ['cod_pre', 'codigo_prestador'],
                'cod_sub': ['cod_sub', 'codigo_subred'],
                'cod_eve': ['cod_eve', 'codigo_evento'],
                'nom_eve': ['nom_eve', 'nombre_evento', 'evento'],
                'fec_not': ['fec_not', 'fecha_notificacion'],
                'nom_upgd': ['nom_upgd', 'nombre_upgd'],
                'nmun_notif': ['nmun_notif', 'municipio_notifica'],
                'tip_ide_': ['tip_ide_', 'tip_ide', 'tipo_identificacion'],
                'num_ide_': ['num_ide_', 'num_ide', 'identificacion', 'documento'],
                'pri_nom_': ['pri_nom_', 'pri_nom', 'primer_nombre'],
                'seg_nom_': ['seg_nom_', 'seg_nom', 'segundo_nombre'],
                'pri_ape_': ['pri_ape_', 'pri_ape', 'primer_apellido'],
                'seg_ape_': ['seg_ape_', 'seg_ape', 'segundo_apellido'],
                'SSSA_AJUSTE': ['sssa_ajuste', 'ajuste_sssa'],
                'RegIniFec': ['reginifec', 'fecha_inicio', 'fecha']
            }

            for _, fila in df_ajustes.iterrows():
                # Preparar valores con mapeo dinámico
                datos = {'actividad_id': id_actividad}
                for interno, posibles in mapa_excel.items():
                    col_encontrada = next((columnas_originales[p] for p in posibles if p in columnas_originales), None)
                    datos[interno] = str(fila[col_encontrada]) if col_encontrada and pd.notnull(fila[col_encontrada]) else ''

                # En Postgres no usamos marcadores nombrados :, usamos %s o diccionarios con %(key)s
                query_insert = """
                    INSERT INTO ajustes (
                        actividad_id, cod_pre, cod_sub, cod_eve, nom_eve, fec_not, nom_upgd, 
                        nmun_notif, tip_ide_, num_ide_, pri_nom_, seg_nom_, pri_ape_, seg_ape_, 
                        SSSA_AJUSTE, RegIniFec
                    ) VALUES (
                        ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
                    )
                """
                cursor.execute(
                    traducir_sql(query_insert),
                    (
                        datos['actividad_id'], datos['cod_pre'], datos['cod_sub'], datos['cod_eve'],
                        datos['nom_eve'], datos['fec_not'], datos['nom_upgd'], datos['nmun_notif'],
                        datos['tip_ide_'], datos['num_ide_'], datos['pri_nom_'], datos['seg_nom_'],
                        datos['pri_ape_'], datos['seg_ape_'], datos['SSSA_AJUSTE'], datos['RegIniFec']
                    )
                )
            conexion.commit()
            logger.info(f"Guardado lote {id_actividad} con {len(df_ajustes)} registros y trazabilidad completa.")
        except Exception as e:
            conexion.rollback()
            logger.error(f"Error crítico en carga masiva de ajustes: {str(e)}")
            raise e

def obtener_ajustes_por_actividad(id_actividad):
    with obtener_conexion() as conexion:
        return pd.read_sql_query(traducir_sql("SELECT * FROM ajustes WHERE actividad_id = ?"), conexion, params=[id_actividad])

def guardar_gestion_granular(ajustes_df):
    with obtener_conexion() as conexion:
        cursor = conexion.cursor()
        try:
            consulta = "UPDATE ajustes SET resultado_rs = ?, nota_tecnica = ?, evidencia_rs = ? WHERE id = ?"
            for _, f in ajustes_df.iterrows():
                cursor.execute(
                    traducir_sql(consulta),
                    (f['resultado_rs'], f['nota_tecnica'], f['evidencia_rs'], f['id'])
                )
            conexion.commit()
            logger.info("Guardados cambios granulares en tabla ajustes.")
        except Exception as e:
            conexion.rollback()
            logger.error(f"Error en guardado granular: {str(e)}")
            raise e

def guardar_validacion_red(ajustes_df):
    with obtener_conexion() as conexion:
        cursor = conexion.cursor()
        try:
            consulta = "UPDATE ajustes SET validacion_red = ? WHERE id = ?"
            for _, f in ajustes_df.iterrows():
                cursor.execute(
                    traducir_sql(consulta),
                    (f['validacion_red'], f['id'])
                )
            conexion.commit()
            logger.info("Guardada validación masiva RED en tabla ajustes.")
        except Exception as e:
            conexion.rollback()
            logger.error(f"Error en validación RED masiva: {str(e)}")
            raise e

# --- Analítica y Reportes ---

def obtener_conteos_estado(rol_usuario, id_usuario=None, ano=None, mes=None, id_subregion=None):
    with obtener_conexion() as conexion:
        consulta = "SELECT status, COUNT(*) as total FROM actividades WHERE 1=1"
        params = []
        if rol_usuario == 'RS':
            consulta += " AND subregion_id = ?"
            params.append(id_subregion)
        elif rol_usuario == 'RED' and id_usuario:
            consulta += " AND created_by = ?"
            params.append(id_usuario)
        if ano:
            consulta += " AND strftime('%Y', created_at) = ?"
            params.append(str(ano))
        if mes:
            consulta += " AND strftime('%m', created_at) = ?"
            params.append(str(mes).zfill(2))
        consulta += " GROUP BY status"
        return pd.read_sql_query(traducir_sql(consulta), conexion, params=params)

def obtener_resumen_ajustes(ano=None, mes=None, id_subregion=None):
    with obtener_conexion() as conexion:
        consulta = """
            SELECT resultado_rs, validacion_red, COUNT(*) as total 
            FROM ajustes aj
            JOIN actividades a ON aj.actividad_id = a.id
            WHERE a.status != 'Anulada'
        """
        params = []
        if id_subregion:
            consulta += " AND a.subregion_id = ?"
            params.append(id_subregion)
        if ano:
            consulta += " AND strftime('%Y', a.created_at) = ?"
            params.append(str(ano))
        if mes:
            consulta += " AND strftime('%m', a.created_at) = ?"
            params.append(str(mes).zfill(2))
        consulta += " GROUP BY resultado_rs, validacion_red"
        return pd.read_sql_query(traducir_sql(consulta), conexion, params=params)

def obtener_productividad_eventos(ano=None, mes=None, id_subregion=None):
    with obtener_conexion() as conexion:
        consulta = """
            SELECT nom_eve as evento, COUNT(*) as total
            FROM ajustes aj
            JOIN actividades a ON aj.actividad_id = a.id
            WHERE a.status != 'Anulada' AND aj.validacion_red = 'Cumplido'
        """
        params = []
        if id_subregion:
            consulta += " AND a.subregion_id = ?"
            params.append(id_subregion)
        if ano:
            consulta += " AND strftime('%Y', a.created_at) = ?"
            params.append(str(ano))
        if mes:
            consulta += " AND strftime('%m', a.created_at) = ?"
            params.append(str(mes).zfill(2))
        consulta += " GROUP BY nom_eve ORDER BY total DESC LIMIT 10"
        return pd.read_sql_query(traducir_sql(consulta), conexion, params=params)

def obtener_actividad_subregional(ano=None, mes=None):
    with obtener_conexion() as conexion:
        consulta = """
            SELECT s.nombre as subregion, COUNT(a.id) as total
            FROM subregiones s
            LEFT JOIN actividades a ON s.id = a.subregion_id
            WHERE 1=1
        """
        params = []
        if ano:
            consulta += " AND strftime('%Y', created_at) = ?"
            params.append(str(ano))
        if mes:
            consulta += " AND strftime('%m', created_at) = ?"
            params.append(str(mes).zfill(2))
        consulta += " GROUP BY s.nombre ORDER BY total DESC"
        return pd.read_sql_query(traducir_sql(consulta), conexion, params=params)

def obtener_anos_disponibles():
    with obtener_conexion() as conexion:
        consulta = "SELECT DISTINCT strftime('%Y', created_at) as year FROM actividades ORDER BY year DESC"
        df = pd.read_sql_query(traducir_sql(consulta), conexion)
        return df['year'].tolist()

def obtener_metricas_sla(ano=None, mes=None, id_subregion=None):
    """Calcula promedios de tiempo y volumen de registros procesados por subregión."""
    with obtener_conexion() as conexion:
        # Traducción manual para JULIANDAY (SQLite) vs EXTRACT EPOCH (Postgres)
        if ES_POSTGRES:
            calc_reaccion = "AVG(EXTRACT(EPOCH FROM (fecha_toma - fecha_asignacion)) / 86400)"
            calc_gestion = "AVG(EXTRACT(EPOCH FROM (fecha_respuesta - fecha_toma)) / 86400)"
            calc_auditoria = "AVG(EXTRACT(EPOCH FROM (fecha_cierre - fecha_respuesta)) / 86400)"
        else:
            calc_reaccion = "AVG(JULIANDAY(fecha_toma) - JULIANDAY(fecha_asignacion))"
            calc_gestion = "AVG(JULIANDAY(fecha_respuesta) - JULIANDAY(fecha_toma))"
            calc_auditoria = "AVG(JULIANDAY(fecha_cierre) - JULIANDAY(fecha_respuesta))"

        consulta = f"""
            SELECT 
                s.nombre as subregion,
                {calc_reaccion} as dias_reaccion,
                {calc_gestion} as dias_gestion,
                {calc_auditoria} as dias_auditoria,
                COUNT(DISTINCT a.id) as total_lotes,
                SUM(COALESCE(aj_count.total, 0)) as total_registros
            FROM subregiones s
            JOIN actividades a ON s.id = a.subregion_id
            LEFT JOIN (
                SELECT actividad_id, COUNT(*) as total 
                FROM ajustes 
                WHERE validacion_red = 'Cumplido'
                GROUP BY actividad_id
            ) aj_count ON a.id = aj_count.actividad_id
            WHERE a.status = 'Cerrada' 
              AND fecha_asignacion IS NOT NULL 
              AND fecha_toma IS NOT NULL 
              AND fecha_respuesta IS NOT NULL 
              AND fecha_cierre IS NOT NULL
        """
        params = []
        if id_subregion:
            consulta += " AND a.subregion_id = ?"
            params.append(id_subregion)
        if ano:
            consulta += " AND strftime('%Y', a.created_at) = ?"
            params.append(str(ano))
        if mes:
            consulta += " AND strftime('%m', a.created_at) = ?"
            params.append(str(mes).zfill(2))
            
        consulta += " GROUP BY s.nombre"
        return pd.read_sql_query(traducir_sql(consulta), conexion, params=params)

def obtener_tendencia_mensual(ano, id_subregion=None):
    """Obtiene el conteo de ajustes cumplidos agrupados por los 12 meses del año."""
    with obtener_conexion() as conexion:
        consulta = """
            SELECT strftime('%m', a.created_at) as mes_num, COUNT(*) as total
            FROM ajustes aj
            JOIN actividades a ON aj.actividad_id = a.id
            WHERE aj.validacion_red = 'Cumplido' AND strftime('%Y', a.created_at) = ?
        """
        params = [str(ano)]
        if id_subregion:
            consulta += " AND a.subregion_id = ?"
            params.append(id_subregion)
        consulta += " GROUP BY mes_num ORDER BY mes_num"
        df_real = pd.read_sql_query(traducir_sql(consulta), conexion, params=params)
        
        # Crear base con los 12 meses
        meses_data = [
            {'num': '01', 'mes': 'Ene'}, {'num': '02', 'mes': 'Feb'},
            {'num': '03', 'mes': 'Mar'}, {'num': '04', 'mes': 'Abr'},
            {'num': '05', 'mes': 'May'}, {'num': '06', 'mes': 'Jun'},
            {'num': '07', 'mes': 'Jul'}, {'num': '08', 'mes': 'Ago'},
            {'num': '09', 'mes': 'Sep'}, {'num': '10', 'mes': 'Oct'},
            {'num': '11', 'mes': 'Nov'}, {'num': '12', 'Dic': 'Dic'}
        ]
        # Corrección del mapeo en Dic
        meses_data[11] = {'num': '12', 'mes': 'Dic'}
        
        df_base = pd.DataFrame(meses_data)
        
        # Unir datos reales con la base de 12 meses
        df_final = pd.merge(df_base, df_real, left_on='num', right_on='mes_num', how='left')
        df_final['total'] = df_final['total'].fillna(0).astype(int)
        
        # Forzar orden cronológico categórico
        lista_meses = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic']
        df_final['mes'] = pd.Categorical(df_final['mes'], categories=lista_meses, ordered=True)
        df_final = df_final.sort_values('mes')
        
        return df_final[['mes', 'total']]

# --- Administración Directa ---

def eliminar_evento(id_evento):
    with obtener_conexion() as conexion:
        try:
            conexion.execute(traducir_sql("DELETE FROM catalog_eventos WHERE id = ?"), (id_evento,))
            conexion.commit()
            logger.info(f"Evento ID {id_evento} eliminado del catálogo.")
        except Exception as e:
            logger.error(f"Error al eliminar evento {id_evento}: {str(e)}")
            raise e

def alternar_estado_usuario(id_usuario, estado_actual):
    nuevo_estado = 0 if estado_actual == 1 else 1
    with obtener_conexion() as conexion:
        try:
            conexion.execute(traducir_sql("UPDATE users SET is_active = ? WHERE id = ?"), (nuevo_estado, id_usuario))
            conexion.commit()
            logger.info(f"Cambio de estado usuario {id_usuario} a {'ACTIVO' if nuevo_estado else 'INACTIVO'}")
        except Exception as e:
            logger.error(f"Error al alternar estado de usuario {id_usuario}: {str(e)}")
            raise e

def agregar_evento(nombre):
    with obtener_conexion() as conexion:
        try:
            conexion.execute(traducir_sql("INSERT INTO catalog_eventos (nombre) VALUES (?)"), (nombre,))
            conexion.commit()
            logger.info(f"Agregado nuevo evento al catálogo: {nombre}")
        except Exception as e:
            logger.error(f"Error al agregar evento {nombre}: {str(e)}")
            raise e

def actualizar_evento(id_evento, nombre):
    with obtener_conexion() as conexion:
        try:
            conexion.execute(traducir_sql("UPDATE catalog_eventos SET nombre = ? WHERE id = ?"), (nombre, id_evento))
            conexion.commit()
            logger.info(f"Actualizado evento {id_evento} a nombre: {nombre}")
        except Exception as e:
            logger.error(f"Error al actualizar evento {id_evento}: {str(e)}")
            raise e

def actualizar_perfil_usuario(id_usuario, nombre_usuario, id_evento=None, id_subregion=None):
    with obtener_conexion() as conexion:
        try:
            conexion.execute(
                traducir_sql("UPDATE users SET username = ?, evento_id = ?, subregion_id = ? WHERE id = ?"),
                (nombre_usuario, id_evento, id_subregion, id_usuario)
            )
            conexion.commit()
            logger.info(f"Perfil de usuario {id_usuario} actualizado a {nombre_usuario}")
        except Exception as e:
            logger.error(f"Error al actualizar perfil de usuario {id_usuario}: {str(e)}")
            raise e

def restablecer_clave_usuario(id_usuario, nuevo_hash_clave):
    with obtener_conexion() as conexion:
        try:
            conexion.execute(traducir_sql("UPDATE users SET password_hash = ? WHERE id = ?"), (nuevo_hash_clave, id_usuario))
            conexion.commit()
            logger.info(f"Contraseña restablecida para usuario ID {id_usuario}")
        except Exception as e:
            logger.error(f"Error al restablecer clave de usuario {id_usuario}: {str(e)}")
            raise e
