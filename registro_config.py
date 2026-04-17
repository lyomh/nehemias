import logging
import os
from logging.handlers import RotatingFileHandler

# Asegurar que el directorio de logs existe
LOGS_DIR = "logs"
if not os.path.exists(LOGS_DIR):
    os.makedirs(LOGS_DIR)

LOG_FILE = os.path.join(LOGS_DIR, "nehemias_servidor.log")

# Configuración del Formato
FORMATO_LOG = logging.Formatter(
    '%(asctime)s | %(levelname)s | [%(filename)s:%(lineno)d] | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

def obtener_registrador(nombre):
    """Retorna un logger configurado con rotación de archivos."""
    registrador = logging.getLogger(nombre)
    
    if not registrador.handlers:
        registrador.setLevel(logging.INFO)
        
        # Handler para archivo con rotación (5MB por archivo, máximo 3 archivos)
        handler_archivo = RotatingFileHandler(
            LOG_FILE, maxBytes=5*1024*1024, backupCount=3, encoding='utf-8'
        )
        handler_archivo.setFormatter(FORMATO_LOG)
        registrador.addHandler(handler_archivo)
        
        # Handler para consola (útil para desarrollo)
        handler_consola = logging.StreamHandler()
        handler_consola.setFormatter(FORMATO_LOG)
        registrador.addHandler(handler_consola)
        
    return registrador
