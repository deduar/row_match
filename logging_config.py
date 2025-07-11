import logging
import sys

# Configurar el logger
# Esto crea un logger llamado "row_match_logger"
logger = logging.getLogger("row_match_logger")
logger.setLevel(logging.DEBUG)  # Captura todos los niveles de logs

# Crear un manejador (handler) para dirigir los logs a la salida estándar (consola)
# Esto es ideal para ver los logs de Docker con `docker-compose logs`
handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.DEBUG)

# Crear un formato para los mensajes de log
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
handler.setFormatter(formatter)

# Añadir el manejador al logger
# Evita añadir handlers duplicados si este módulo se recarga
if not logger.handlers:
    logger.addHandler(handler)
