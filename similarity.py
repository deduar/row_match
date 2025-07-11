import numpy as np
import re

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

def calculate_structural_similarity(text1: str, text2: str) -> float:
    """
    Calcula una puntuación de similitud estructural basada en la coincidencia de
    códigos numéricos largos (5 o más dígitos).

    Args:
        text1: El primer fragmento de texto.
        text2: El segundo fragmento de texto.

    Returns:
        1.0 si se encuentra una coincidencia de código, 0.0 en caso contrario.
    """
    # Expresión regular para encontrar secuencias de 5 o más dígitos.
    # Esto ayuda a filtrar números pequeños y enfocarse en posibles IDs o referencias.
    regex = re.compile(r'\d{5,}')
    
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
