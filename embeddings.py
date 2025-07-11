from sentence_transformers import SentenceTransformer
from typing import List
import numpy as np

# Carga el modelo una sola vez cuando se importa el módulo.
# Esto es eficiente ya que evita recargar el modelo en cada llamada a la API.
# El modelo se descargará automáticamente la primera vez que se ejecute.
model = SentenceTransformer('all-MiniLM-L6-v2')

def get_embeddings(chunks: List[str]) -> List[List[float]]:
    """
    Genera embeddings para una lista de fragmentos de texto.

    Args:
        chunks: Una lista de strings (fragmentos de texto).

    Returns:
        Una lista de vectores de embedding, donde cada vector es una lista de floats.
    """
    if not chunks:
        return []
        
    # El método encode devuelve un array de numpy, lo convertimos a lista para que sea serializable en JSON.
    embeddings = model.encode(chunks, convert_to_tensor=False)
    return embeddings.tolist()
