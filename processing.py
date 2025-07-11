import io
import pathlib
from typing import List

import pandas as pd
import pytesseract
from PIL import Image
import fitz  # PyMuPDF

from logging_config import logger

# --- Manejadores para cada tipo de archivo ---

def _handle_pdf(file_content: bytes) -> List[str]:
    """Extrae texto de un archivo PDF, fragmentando por líneas."""
    chunks = []
    try:
        with fitz.open(stream=file_content, filetype="pdf") as doc:
            logger.info(f"Procesando PDF con {len(doc)} páginas.")
            for i, page in enumerate(doc):
                logger.debug(f"Extrayendo texto de la página {i+1}/{len(doc)}")
                text = page.get_text("text", sort=True) # sort=True para un orden de lectura más natural
                chunks.extend(text.splitlines())
            logger.info("Extracción de texto del PDF completada.")
    except Exception as e:
        logger.error(f"Error procesando el archivo PDF: {e}", exc_info=True)
        return [f"Error procesando el archivo PDF: {e}"]
    return [chunk.strip() for chunk in chunks if chunk.strip()]

def _handle_tabular(file_content: bytes, extension: str) -> List[str]:
    """
    Extrae texto de archivos tabulares (CSV, XLS, XLSX) o de tablas en HTML.
    Intenta leer el archivo como Excel y, si falla, como HTML.
    """
    chunks = []
    df_list = [] # read_html devuelve una lista de DataFrames

    try:
        logger.info(f"Procesando archivo tabular con extensión {extension}.")
        if extension == ".csv":
            df = pd.read_csv(io.BytesIO(file_content))
            df_list.append(df)
        elif extension == ".xls":
            df = pd.read_excel(io.BytesIO(file_content), engine='xlrd')
            df_list.append(df)
        else:  # .xlsx
            df = pd.read_excel(io.BytesIO(file_content))
            df_list.append(df)
        
        logger.info(f"Archivo tabular cargado exitosamente como formato Excel.")

    except Exception as e:
        # Si falla la lectura como Excel, intentamos como HTML.
        # Esto es común para archivos .xls exportados desde sistemas web.
        logger.warning(f"Falló la lectura como Excel ({e}). Intentando leer como tabla HTML.")
        try:
            # read_html espera una string, no bytes, así que decodificamos.
            # Usamos 'ignore' para evitar errores con caracteres extraños.
            html_string = file_content.decode('utf-8', errors='ignore')
            # read_html devuelve una lista de todos los dataframes encontrados en el HTML
            dfs = pd.read_html(io.StringIO(html_string))
            df_list.extend(dfs)
            logger.info(f"Archivo leído exitosamente como HTML. Se encontraron {len(df_list)} tablas.")
        except Exception as html_error:
            # Si ambos fallan, registramos el error final y retornamos.
            logger.error(f"Error procesando el archivo como Excel y como HTML: {html_error}", exc_info=True)
            return [f"Error procesando archivo: No es un formato de tabla válido (Excel/HTML). Error: {html_error}"]

    # Procesar todos los DataFrames encontrados (normalmente uno, pero pueden ser más si es HTML)
    for df in df_list:
        logger.info(f"Procesando un DataFrame con {len(df)} filas.")
        for _, row in df.iterrows():
            row_str = ", ".join(str(item) for item in row.dropna().values)
            if row_str:
                chunks.append(row_str)
                
    logger.info(f"Procesamiento de archivo tabular completado. Se extrajeron {len(chunks)} chunks.")
    return [chunk.strip() for chunk in chunks if chunk.strip()]

def _handle_image(file_content: bytes) -> List[str]:
    """Extrae texto de un archivo de imagen usando OCR, fragmentando por líneas."""
    chunks = []
    try:
        logger.info("Procesando archivo de imagen con Tesseract OCR.")
        image = Image.open(io.BytesIO(file_content))
        # Se puede especificar el idioma si se conoce, ej. lang='eng+spa'
        text = pytesseract.image_to_string(image)
        chunks.extend(text.splitlines())
        logger.info(f"OCR completado. Se extrajeron {len(chunks)} líneas.")
    except Exception as e:
        logger.error(f"Error procesando el archivo de imagen: {e}", exc_info=True)
        return [f"Error procesando el archivo de imagen: {e}"]
    
    return [chunk.strip() for chunk in chunks if chunk.strip()]

def _handle_text(file_content: bytes) -> List[str]:
    """Extrae texto de un archivo de texto plano, fragmentando por líneas."""
    chunks = []
    try:
        logger.info("Procesando como archivo de texto plano.")
        # Intenta decodificar con UTF-8, el más común
        text = file_content.decode('utf-8')
        chunks.extend(text.splitlines())
        logger.info("Decodificación con UTF-8 exitosa.")
    except UnicodeDecodeError:
        logger.warning("Falló la decodificación con UTF-8, intentando con latin-1.")
        try:
            # Si falla, intenta con latin-1, común en algunos sistemas
            text = file_content.decode('latin-1')
            chunks.extend(text.splitlines())
            logger.info("Decodificación con latin-1 exitosa.")
        except Exception as e:
            logger.error(f"Error de decodificación en el archivo de texto: {e}", exc_info=True)
            return [f"Error de decodificación en el archivo de texto: {e}"]
            
    return [chunk.strip() for chunk in chunks if chunk.strip()]

# --- Función principal de despacho ---

def extract_chunks_from_file(file_content: bytes, filename: str) -> List[str]:
    """
    Extrae fragmentos de texto de un archivo basándose en su extensión.

    Args:
        file_content: El contenido en bytes del archivo.
        filename: El nombre del archivo.

    Returns:
        Una lista de fragmentos de texto extraídos del archivo.
    """
    extension = pathlib.Path(filename).suffix.lower()
    logger.info(f"Iniciando extracción de chunks para el archivo '{filename}' con extensión '{extension}'.")

    if extension == ".pdf":
        return _handle_pdf(file_content)
    elif extension in [".xls", ".xlsx", ".csv"]:
        return _handle_tabular(file_content, extension)
    elif extension in [".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tiff"]:
        return _handle_image(file_content)
    elif extension in [".txt", ".md", ".py", ".js", ".html", ".css"]:
        return _handle_text(file_content)
    else:
        logger.warning(f"Extensión '{extension}' no reconocida. Intentando procesar como archivo de texto plano por defecto.")
        # Como fallback, intenta procesarlo como un archivo de texto.
        # Esto puede funcionar para muchos tipos de archivo basados en texto sin extensión conocida.
        return _handle_text(file_content)
