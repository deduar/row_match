import streamlit as st
import requests
import pandas as pd
import os
import time

# --- Configuración de la Página y API ---

# Título de la página y layout
st.set_page_config(page_title="Conciliador de Archivos", layout="wide")

# Obtener la URL de la API desde las variables de entorno (configurado en docker-compose)
API_URL = os.getenv("API_URL", "http://localhost:8000")

# --- Funciones de Interacción con la API ---

def get_files_from_collection(collection_name):
    """Obtiene la lista de archivos de una colección desde la API."""
    try:
        response = requests.get(f"{API_URL}/files/{collection_name}")
        response.raise_for_status()
        return response.json().get("files", [])
    except requests.exceptions.RequestException as e:
        st.error(f"Error al conectar con la API para obtener archivos: {e}")
        return []

def upload_file(collection_name, uploaded_file):
    """Sube un archivo a una colección específica a través de la API."""
    if uploaded_file is None:
        return None

    # Verificar si un archivo con el mismo nombre ya existe
    existing_files = get_files_from_collection(collection_name)
    if any(f['filename'] == uploaded_file.name for f in existing_files):
        st.warning(f"Un archivo con el nombre '{uploaded_file.name}' ya existe en la colección. No se procesará de nuevo.")
        return None
    
    files = {'file': (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)}
    try:
        with st.spinner(f"Procesando '{uploaded_file.name}'... Esto puede tardar unos segundos."):
            response = requests.post(f"{API_URL}/process-file/{collection_name}", files=files)
        
        if response.status_code == 409: # Conflict
            st.warning(f"El contenido del archivo '{uploaded_file.name}' ya ha sido procesado anteriormente en esta colección.")
            return None
        
        response.raise_for_status()
        st.success(f"¡Archivo '{uploaded_file.name}' procesado y guardado exitosamente!")
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Error al subir el archivo: {e.response.json() if e.response else e}")
        return None

def match_files(bank_hash, fm_hash, threshold):
    """Llama al endpoint de matching de la API."""
    payload = {
        "bank_movements_hash": bank_hash,
        "fm_report_hash": fm_hash
    }
    try:
        with st.spinner("Realizando conciliación... Este proceso puede ser largo dependiendo del tamaño de los archivos."):
            response = requests.post(f"{API_URL}/match-files?min_score_threshold={threshold}", json=payload)
            response.raise_for_status()
        st.success("¡Conciliación completada!")
        return response.json().get("match_results", [])
    except requests.exceptions.RequestException as e:
        st.error(f"Error durante la conciliación: {e.response.json() if e.response else e}")
        return None

# --- Interfaz de Usuario ---

st.title("📄 Interfaz de Conciliación de Archivos")
st.markdown("Sube, visualiza y concilia los reportes de Fuerza Móvil con los movimientos bancarios.")

# --- Sección 1: Carga de Archivos ---
st.header("1. Cargar Nuevos Archivos")

col1, col2 = st.columns(2)

with col1:
    st.subheader("Reporte de Fuerza Móvil")
    fm_file = st.file_uploader("Selecciona un archivo de reporte (.xlsx, .csv)", key="fm_uploader")
    if st.button("Procesar Reporte de FM"):
        if fm_file:
            upload_file("FMReport", fm_file)
            # Pequeña pausa para que el usuario vea el mensaje de éxito
            time.sleep(2)
            st.rerun()
        else:
            st.warning("Por favor, selecciona un archivo de reporte primero.")

with col2:
    st.subheader("Movimientos Bancarios")
    bank_file = st.file_uploader("Selecciona un archivo de banco (.pdf, .xls, etc.)", key="bank_uploader")
    if st.button("Procesar Movimientos de Banco"):
        if bank_file:
            upload_file("BankMovements", bank_file)
            time.sleep(2)
            st.rerun()
        else:
            st.warning("Por favor, selecciona un archivo de banco primero.")

st.divider()

# --- Sección 2: Conciliación ---
st.header("2. Realizar Conciliación")

# Obtener listas de archivos
fm_files = get_files_from_collection("FMReport")
bank_files = get_files_from_collection("BankMovements")

# Crear diccionarios para mapear nombres de archivo a hashes
fm_options = {f'{f["filename"]} ({f["file_hash"][:8]}...)': f["file_hash"] for f in fm_files}
bank_options = {f'{f["filename"]} ({f["file_hash"][:8]}...)': f["file_hash"] for f in bank_files}

if not fm_files or not bank_files:
    st.info("Necesitas subir al menos un archivo a cada colección para poder realizar la conciliación.")
else:
    col3, col4 = st.columns(2)
    with col3:
        selected_fm_display = st.selectbox("Selecciona el Reporte de FM a conciliar:", options=fm_options.keys())
    with col4:
        selected_bank_display = st.selectbox("Selecciona el archivo de Movimientos de Banco:", options=bank_options.keys())

    threshold = st.slider("Umbral de Confianza (Score Combinado Mínimo):", min_value=0.0, max_value=1.0, value=0.8, step=0.05)

    if st.button("Iniciar Conciliación", type="primary"):
        selected_fm_hash = fm_options[selected_fm_display]
        selected_bank_hash = bank_options[selected_bank_display]
        
        results = match_files(selected_bank_hash, selected_fm_hash, threshold)
        
        if results is not None:
            st.subheader(f"Resultados de la Conciliación ({len(results)} coincidencias encontradas)")
            
            if not results:
                st.warning("No se encontraron coincidencias que superen el umbral de confianza especificado.")
            else:
                # Preparar datos para el DataFrame
                display_data = []
                for res in results:
                    display_data.append({
                        "Movimiento Bancario": res["bank_movement_chunk"]["document"],
                        "Mejor Coincidencia en Reporte": res["best_match_in_fm_report"]["fm_chunk_document"],
                        "Score Combinado": f'{res["best_match_in_fm_report"]["combined_score"]:.2f}',
                        "Similitud Semántica": f'{res["best_match_in_fm_report"]["cosine_similarity"]:.2f}',
                        "Similitud Estructural": f'{res["best_match_in_fm_report"]["structural_similarity"]:.2f}',
                    })
                
                df = pd.DataFrame(display_data)
                st.dataframe(df, use_container_width=True)