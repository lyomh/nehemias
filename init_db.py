from database import inicializar_db, obtener_conexion, registrar_accion, traducir_sql
from auth import generar_hash_clave

SUBREGIONES_ANTIOQUIA = [
    "Bajo Cauca",
    "Magdalena Medio",
    "Nordeste",
    "Norte",
    "Occidente",
    "Oriente",
    "Suroeste",
    "Urabá",
    "Valle de Aburrá"
]

EVENTOS_VIGILANCIA = [
    "Evento 359 (Adulto/Pediátrico)",
    "Tuberculosis",
    "VIH / Sida",
    "Salud Mental",
    "Vigilancia de Mortalidad",
    "Enfermedades Transmitidas por Vectores",
    "Zoonosis",
    "Inmunoprevenibles"
]

def seed_data():
    """Puebla la base de datos con subregiones, eventos y administradores iniciales."""
    # Re-inicializar esquema
    inicializar_db()
    
    with obtener_conexion() as conn:
        cursor = conn.cursor()
        
        # 1. Cargar Subregiones
        for nombre in SUBREGIONES_ANTIOQUIA:
            cursor.execute(traducir_sql("INSERT OR IGNORE INTO subregiones (nombre) VALUES (?)"), (nombre,))
        
        # 2. Cargar Catálogo de Eventos
        for evento in EVENTOS_VIGILANCIA:
            cursor.execute(traducir_sql("INSERT OR IGNORE INTO catalog_eventos (nombre) VALUES (?)"), (evento,))
        
        # 3. Crear Administradores por Defecto
        users_to_seed = [
            ("admin_central", "Nehemias2026*", "ARD"),
            ("admin_territorial", "Nehemias2026*", "ART")
        ]
        
        for username, password, role in users_to_seed:
            hashed = generar_hash_clave(password)
            try:
                cursor.execute(
                    traducir_sql("INSERT INTO users (username, password_hash, role, created_by) VALUES (?, ?, ?, NULL)"),
                    (username, hashed, role)
                )
                print(f"✅ Usuario {role} creado: {username}")
            except:
                pass # Ya existe
                
        conn.commit()
    print("🚀 Base de Datos Reinicializada (Manual 2024-2027 aplicado).")

if __name__ == "__main__":
    seed_data()
