from fastapi import FastAPI, File, UploadFile, HTTPException
from typing import Dict, Any
from enum import Enum
import hashlib
from pydantic import BaseModel

# Importa la lógica de los otros módulos
import processing
import embeddings
from logging_config import logger
from database import (
    save_chunks_to_db, 
    get_chunks_from_db, 
    clear_collection, 
    check_if_hash_exists, 
    get_chunk_by_id,
    get_all_chunks_by_hash,
    get_distinct_files_in_collection # <-- Importar la nueva función
)
from similarity import calculate_cosine_similarity, calculate_structural_similarity

# --- Modelos de Datos para Validación ---

class CollectionName(str, Enum):
    fm_report = "FMReport"
    bank_movements = "BankMovements"

class ComparisonItem(BaseModel):
    collection_name: CollectionName
    item_id: str

class ComparisonRequest(BaseModel):
    item1: ComparisonItem
    item2: ComparisonItem
    min_digits: int = 5
    min_digits: int = 5

class MatchFilesRequest(BaseModel):
    bank_movements_hash: str
    fm_report_hash: str

# --- Aplicación FastAPI ---

app = FastAPI(
    title="API para Procesamiento de Archivos y Generación de Embeddings",
    description="Sube, explora, compara y haz matching de archivos a través de embeddings vectoriales.",
    version="1.5.0", # Versión incrementada
)

@app.post("/process-file/{collection_name}", 
          summary="Procesa un archivo y lo guarda en una colección específica",
          responses={409: {"description": "El archivo ya ha sido procesado."}})
async def create_embeddings_from_file(collection_name: CollectionName, file: UploadFile = File(...)):
    filename = file.filename if file.filename else "unknown_file"
    logger.info(f"Recibida petición para procesar '{filename}' en la colección '{collection_name.value}'")
    
    try:
        file_content = await file.read()
    finally:
        await file.close()

    file_hash = hashlib.sha256(file_content).hexdigest()
    if check_if_hash_exists(collection_name.value, file_hash):
        raise HTTPException(status_code=409, detail=f"Este contenido de archivo ya existe en la colección '{collection_name.value}'.")

    chunks = processing.extract_chunks_from_file(file_content, filename)
    if not chunks:
        raise HTTPException(status_code=404, detail="No se pudo extraer contenido del archivo.")
    
    chunk_embeddings = embeddings.get_embeddings(chunks)
    num_saved = save_chunks_to_db(collection_name.value, filename, file_hash, chunks, chunk_embeddings)

    return {
        "collection": collection_name.value,
        "filename": filename,
        "file_hash": file_hash,
        "chunks_extracted": len(chunks),
        "chunks_saved_to_db": num_saved,
        "status": "Procesamiento y guardado completados."
    }

@app.post("/match-files",
          summary="Realiza un matching entre un archivo de movimientos bancarios y un reporte de FM")
def match_files(request: MatchFilesRequest, min_score_threshold: float = 0.8, min_digits: int = 5):
    logger.info(f"Iniciando proceso de matching con umbral de score >= {min_score_threshold}")
    bank_chunks = get_all_chunks_by_hash(CollectionName.bank_movements.value, request.bank_movements_hash)
    fm_chunks = get_all_chunks_by_hash(CollectionName.fm_report.value, request.fm_report_hash)

    if isinstance(bank_chunks, dict) and "error" in bank_chunks or not bank_chunks:
        raise HTTPException(status_code=404, detail=f"No se encontraron chunks para el hash de movimientos bancarios: {request.bank_movements_hash}")
    if isinstance(fm_chunks, dict) and "error" in fm_chunks or not fm_chunks:
        raise HTTPException(status_code=404, detail=f"No se encontraron chunks para el hash del reporte FM: {request.fm_report_hash}")

    match_results = []
    for bank_chunk in bank_chunks:
        best_match = {"fm_chunk_id": None, "combined_score": -1.0}
        for fm_chunk in fm_chunks:
            cosine_sim = calculate_cosine_similarity(bank_chunk["embedding"], fm_chunk["embedding"])
            struct_sim = calculate_structural_similarity(bank_chunk["document"], fm_chunk["document"], min_digits)
            combined_score = (0.7 * struct_sim) + (0.3 * cosine_sim)
            if combined_score > best_match["combined_score"]:
                best_match = {
                    "fm_chunk_id": fm_chunk["id"], "combined_score": combined_score,
                    "cosine_similarity": cosine_sim, "structural_similarity": struct_sim,
                    "fm_chunk_document": fm_chunk["document"]
                }
        if best_match["combined_score"] >= min_score_threshold:
            match_results.append({
                "bank_movement_chunk": {"id": bank_chunk["id"], "document": bank_chunk["document"]},
                "best_match_in_fm_report": best_match
            })
    return {"match_results": match_results}

@app.get("/files/{collection_name}",
         summary="Lista los archivos procesados en una colección")
def list_files_in_collection(collection_name: CollectionName):
    """
    Devuelve una lista de archivos únicos (nombre y hash) que han sido
    procesados y guardados en la colección especificada.
    """
    logger.info(f"Recibida petición para listar archivos en la colección '{collection_name.value}'.")
    files = get_distinct_files_in_collection(collection_name.value)
    if isinstance(files, dict) and "error" in files:
        raise HTTPException(status_code=500, detail=files["error"])
    return {"files": files}

@app.post("/compare", summary="Compara dos chunks y calcula su similitud semántica")
def compare_two_chunks(request: ComparisonRequest):
    item1_data = get_chunk_by_id(request.item1.collection_name.value, request.item1.item_id)
    if not item1_data or "error" in item1_data:
        raise HTTPException(status_code=404, detail=f"Item 1 con ID '{request.item1.item_id}' no encontrado.")
    item2_data = get_chunk_by_id(request.item2.collection_name.value, request.item2.item_id)
    if not item2_data or "error" in item2_data:
        raise HTTPException(status_code=404, detail=f"Item 2 con ID '{request.item2.item_id}' no encontrado.")
    cosine_score = calculate_cosine_similarity(item1_data.get("embedding"), item2_data.get("embedding"))
    structural_score = calculate_structural_similarity(item1_data.get("document", ""), item2_data.get("document", ""), request.min_digits)
    return {
        "cosine_similarity": cosine_score, "structural_similarity": structural_score,
        "item1": {"id": item1_data["id"], "document": item1_data["document"], "metadata": item1_data["metadata"]},
        "item2": {"id": item2_data["id"], "document": item2_data["document"], "metadata": item2_data["metadata"]}
    }

@app.get("/chunks/{collection_name}/{item_id}", summary="Obtiene un chunk específico por su ID")
def get_single_chunk(collection_name: CollectionName, item_id: str):
    item = get_chunk_by_id(collection_name.value, item_id)
    if not item:
        raise HTTPException(status_code=404, detail=f"Chunk con ID '{item_id}' no encontrado.")
    if "error" in item:
        raise HTTPException(status_code=500, detail=item["error"])
    return item

@app.get("/chunks/{collection_name}", summary="Explora los chunks de una colección específica")
def get_stored_chunks(collection_name: CollectionName, limit: int = 100, offset: int = 0):
    data = get_chunks_from_db(collection_name.value, limit=limit, offset=offset)
    if "error" in data:
        raise HTTPException(status_code=500, detail=data["error"])
    return data

@app.delete("/chunks/{collection_name}", summary="[DEV] Limpia todos los datos de una colección específica")
def delete_all_chunks(collection_name: CollectionName):
    success, message = clear_collection(collection_name.value)
    if not success:
        raise HTTPException(status_code=500, detail=message)
    return {"status": message}

@app.get("/", summary="Endpoint de bienvenida", include_in_schema=False)
def read_root():
    return {"message": "Bienvenido a la API de procesamiento de archivos. Visita /docs para la documentación interactiva."}
