import chromadb
import os
from logging_config import logger

# Lee el host de ChromaDB desde las variables de entorno definidas en docker-compose.yml
CHROMA_HOST = os.getenv("CHROMA_HOST", "localhost")

logger.info(f"Intentando conectar con ChromaDB en el host: {CHROMA_HOST}")

try:
    # Inicializa el cliente de ChromaDB para conectarse al servidor
    client = chromadb.HttpClient(host=CHROMA_HOST, port=8000)
    logger.info("Conexión con ChromaDB establecida exitosamente.")

except Exception as e:
    logger.critical(f"No se pudo conectar a ChromaDB en '{CHROMA_HOST}': {e}", exc_info=True)
    client = None

def save_chunks_to_db(collection_name: str, filename: str, file_hash: str, chunks: list, embeddings: list):
    """
    Guarda los chunks, embeddings y metadatos (incluyendo el hash del archivo) 
    en una colección específica de ChromaDB.
    """
    if not client:
        logger.error("La conexión con la base de datos no está disponible. No se guardarán los chunks.")
        return 0
    
    if not chunks:
        logger.warning("No hay chunks para guardar en la base de datos.")
        return 0

    try:
        collection = client.get_or_create_collection(name=collection_name)
        logger.info(f"Colección '{collection_name}' lista para la inserción.")
    except Exception as e:
        logger.error(f"No se pudo obtener o crear la colección '{collection_name}': {e}", exc_info=True)
        return 0

    # Genera IDs únicos y deterministas basados en el hash del contenido del archivo.
    ids = [f"{file_hash}-{i}" for i in range(len(chunks))]
    # Añade el hash del archivo a los metadatos de cada chunk.
    metadatas = [
        {"source_filename": filename, "file_hash": file_hash, "chunk_index": i} 
        for i in range(len(chunks))
    ]
    
    try:
        logger.info(f"Guardando {len(chunks)} chunks del archivo '{filename}' en la colección '{collection_name}'.")
        # Usamos 'add' que funciona como "upsert". Si los IDs ya existen, se sobrescriben.
        collection.add(
            embeddings=embeddings,
            documents=chunks,
            metadatas=metadatas,
            ids=ids
        )
        logger.info("Chunks guardados en la base de datos exitosamente.")
        return len(chunks)
    except Exception as e:
        logger.error(f"Error al guardar chunks en ChromaDB: {e}", exc_info=True)
        return 0

def check_if_hash_exists(collection_name: str, file_hash: str) -> bool:
    """
    Verifica si algún documento con un file_hash específico ya existe en la colección.
    """
    if not client:
        logger.error("La conexión con la base de datos no está disponible. No se puede verificar el hash.")
        return False
    
    try:
        collection = client.get_collection(name=collection_name)
        # Usamos un filtro 'where' para buscar metadatos que coincidan con el hash.
        # Limitamos a 1 porque solo necesitamos saber si existe al menos uno.
        results = collection.get(where={"file_hash": file_hash}, limit=1)
        
        # Si la lista de IDs devuelta no está vacía, significa que el hash existe.
        return len(results["ids"]) > 0
    except Exception:
        # Si la colección no existe, es seguro decir que el hash tampoco.
        logger.warning(f"La colección '{collection_name}' no existe aún. El hash no puede existir.")
        return False

def get_chunks_from_db(collection_name: str, limit: int = 100, offset: int = 0):
    """
    Obtiene chunks de una colección específica con paginación.
    """
    if not client:
        msg = "La conexión con la base de datos no está disponible."
        logger.error(msg)
        return {"error": msg}

    try:
        collection = client.get_collection(name=collection_name)
        logger.info(f"Obteniendo chunks de la colección '{collection_name}' con limit={limit} y offset={offset}.")
        
        total_items = collection.count()
        results = collection.get(limit=limit, offset=offset, include=["metadatas", "documents"])
        
        items = [
            {"id": id, "document": doc, "metadata": meta}
            for id, doc, meta in zip(results["ids"], results["documents"], results["metadatas"])
        ]

        return {"collection_name": collection_name, "total_items_in_collection": total_items, "items_returned": len(items), "items": items}

    except Exception as e:
        # Captura el caso en que la colección no exista
        logger.error(f"Error al obtener chunks de la colección '{collection_name}': {e}", exc_info=True)
        return {"error": f"Error al obtener chunks de la colección '{collection_name}': {e}"}

def clear_collection(collection_name: str):
    """
    Elimina y recrea una colección específica, borrando todos sus datos.
    """
    if not client:
        msg = "La conexión con la base de datos no está disponible."
        logger.error(msg)
        return False, msg

    try:
        logger.warning(f"Iniciando operación de borrado para la colección: '{collection_name}'")
        client.delete_collection(name=collection_name)
        
        logger.info(f"Colección '{collection_name}' eliminada. Recreándola...")
        client.get_or_create_collection(name=collection_name)
        
        msg = f"Colección '{collection_name}' limpiada y recreada exitosamente."
        logger.info(msg)
        return True, msg
    except Exception as e:
        msg = f"Ocurrió un error al intentar limpiar la colección '{collection_name}': {e}"
        logger.critical(msg, exc_info=True)
        return False, msg

def get_chunk_by_id(collection_name: str, item_id: str):
    """
    Obtiene un único chunk por su ID de una colección específica, incluyendo su embedding.
    """
    if not client:
        msg = "La conexión con la base de datos no está disponible."
        logger.error(msg)
        return {"error": msg}

    try:
        collection = client.get_collection(name=collection_name)
        # Usamos get() con el ID específico.
        # Incluimos 'embeddings' para obtener el vector completo.
        result = collection.get(
            ids=[item_id],
            include=["metadatas", "documents", "embeddings"]
        )

        # Si la lista de IDs devuelta está vacía, el item no fue encontrado.
        if not result["ids"]:
            return None

        # Obtenemos el embedding, que es un numpy.ndarray
        embedding_vector = result["embeddings"][0]

        # Re-estructuramos la respuesta, convirtiendo explícitamente el embedding a una lista de Python.
        item = {
            "id": result["ids"][0],
            "document": result["documents"][0],
            "metadata": result["metadatas"][0],
            # El método .tolist() convierte el array de numpy en una lista estándar de Python
            "embedding": embedding_vector.tolist() if embedding_vector is not None else None
        }
        return item

    except Exception as e:
        logger.error(f"Error al obtener el chunk '{item_id}' de la colección '{collection_name}': {e}", exc_info=True)
        return {"error": f"Error al obtener el chunk: {e}"}

def get_all_chunks_by_hash(collection_name: str, file_hash: str):
    """
    Obtiene todos los chunks (con embeddings) de un archivo específico usando su hash.
    """
    if not client:
        msg = "La conexión con la base de datos no está disponible."
        logger.error(msg)
        return {"error": msg}

    try:
        collection = client.get_collection(name=collection_name)
        
        logger.info(f"Recuperando todos los chunks de la colección '{collection_name}' con hash '{file_hash}'.")
        
        # CORRECCIÓN: Llamar a get() directamente con el filtro 'where'.
        # No se cuenta primero, ya que count() no soporta filtros.
        results = collection.get(
            where={"file_hash": file_hash},
            include=["metadatas", "documents", "embeddings"]
        )
        
        if not results["ids"]:
            return [] # Devuelve una lista vacía si no se encontró nada.

        # Re-estructuramos los datos en una lista de diccionarios para fácil manejo
        items = [
            {
                "id": id,
                "document": doc,
                "metadata": meta,
                "embedding": emb # El embedding ya es una lista aquí, no necesita .tolist()
            }
            for id, doc, meta, emb in zip(results["ids"], results["documents"], results["metadatas"], results["embeddings"])
        ]
        return items

    except Exception as e:
        logger.error(f"Error al obtener todos los chunks por hash '{file_hash}': {e}", exc_info=True)
        return {"error": f"Error al obtener chunks por hash: {e}"}

def get_distinct_files_in_collection(collection_name: str):
    """
    Obtiene una lista de archivos únicos (nombre y hash) que han sido procesados
    en una colección específica.
    """
    if not client:
        msg = "La conexión con la base de datos no está disponible."
        logger.error(msg)
        return {"error": msg}

    try:
        collection = client.get_collection(name=collection_name)
        # Obtenemos solo los metadatos para que la consulta sea ligera
        results = collection.get(include=["metadatas"])

        if not results["ids"]:
            return []

        # Usamos un set de tuplas para obtener combinaciones únicas de nombre y hash
        unique_files = {(meta.get("source_filename"), meta.get("file_hash")) for meta in results["metadatas"]}
        
        # Convertimos el set a una lista de diccionarios para la respuesta JSON
        return [{"filename": filename, "file_hash": file_hash} for filename, file_hash in unique_files if filename and file_hash]
        
    except Exception as e:
        # Si la colección no existe, devolvemos una lista vacía, lo cual es esperado.
        logger.warning(f"No se pudo obtener la colección '{collection_name}' (puede que no exista aún): {e}")
        return []
