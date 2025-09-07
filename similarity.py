import numpy as np
import re
from logging_config import logger

def calculate_cosine_similarity(vec1: list[float], vec2: list[float]) -> float:
    """
    Calcula la similitud de coseno entre dos vectores.
    """
    # CORRECCIÓN: Comprobar explícitamente si los vectores son None o están vacíos.
    if vec1 is None or vec2 is None or len(vec1) == 0 or len(vec2) == 0:
        return 0.0
        
    v1 = np.array(vec1)
    v2 = np.array(vec2)
    dot_product = np.dot(v1, v2)
    norm_v1 = np.linalg.norm(v1)
    norm_v2 = np.linalg.norm(v2)
    epsilon = 1e-8
    similarity = dot_product / ((norm_v1 * norm_v2) + epsilon)
    return float(similarity)

def is_institutional_info(text: str) -> bool:
    """
    Determina si un texto contiene información institucional bancaria.
    
    Args:
        text: El texto a evaluar
        
    Returns:
        True si el texto parece ser información institucional, False en caso contrario
    """
    # Convertir a minúsculas para comparaciones insensibles a mayúsculas/minúsculas
    text_lower = text.lower()
    
    # Lista de palabras clave que indican información institucional
    institutional_keywords = [
        "banco", "universal", "capital", "autorizado", "suscrito", "pagado",
        "rif", "j-", "apartado", "postal", "c.a.", "s.a.", "compañía anónima",
        "mercantil", "banesco", "bbva", "provincial", "venezuela", "estado de cuenta",
        "resumen de movimientos", "detalle de movimientos", "titular", "situación al",
        "nro. de cuenta", "f. oper", "f. valor", "abonos", "cargos", "saldo"
    ]
    
    # Verificar si contiene al menos 2 palabras clave institucionales
    keyword_count = sum(1 for keyword in institutional_keywords if keyword in text_lower)
    if keyword_count >= 2:
        return True
    
    # Patrones específicos de información institucional
    institutional_patterns = [
        r'(?i)banco\s+\w+',  # Nombre de banco
        r'(?i)capital\s+(autorizado|suscrito|pagado)',  # Información de capital
        r'(?i)rif\.?\s*[a-z]-\d+',  # Formato de RIF
        r'(?i)apartado\s+postal',  # Apartado postal
        r'(?i)estado\s+de\s+cuenta',  # Título del estado de cuenta
        r'(?i)titular\s*:',  # Titular de la cuenta
        r'(?i)situaci[óo]n\s+al\s*:',  # Fecha de situación
        r'(?i)nro\.\s+de\s+cuenta\s*:',  # Número de cuenta
    ]
    
    for pattern in institutional_patterns:
        if re.search(pattern, text):
            return True
    
    return False

def calculate_structural_similarity(text1: str, text2: str, min_digits: int = 5) -> float:
    """
    Calcula una puntuación de similitud estructural basada en la coincidencia de
    códigos numéricos largos.

    Args:
        text1: El primer fragmento de texto.
        text2: El segundo fragmento de texto.
        min_digits: El número mínimo de dígitos para considerar un código.

    Returns:
        1.0 si se encuentra una coincidencia de código, 0.0 en caso contrario.
    """
    # Verificar si alguno de los textos contiene información institucional
    if is_institutional_info(text1) or is_institutional_info(text2):
        logger.info(f"Similitud estructural: Detectada información institucional, retornando 0.0")
        logger.debug(f"Texto 1: {text1[:50]}...")
        logger.debug(f"Texto 2: {text2[:50]}...")
        return 0.0  # No permitir coincidencias con información institucional
    
    # Expresión regular para encontrar secuencias de 'min_digits' o más dígitos.
    # Esto ayuda a filtrar números pequeños y enfocarse en posibles IDs o referencias.
    regex = re.compile(rf'\d{{{min_digits},}}')
    
    # Extraer todos los "códigos" de cada texto.
    codes1 = set(regex.findall(text1))
    codes2 = set(regex.findall(text2))

    if not codes1 or not codes2:
        return 0.0

    # Comprobar si algún código de una lista es un substring de un código de la otra.
    for c1 in codes1:
        for c2 in codes2:
            if c1 in c2 or c2 in c1:
                return 1.0  # Se encontró una coincidencia

    return 0.0  # No se encontraron coincidencias
