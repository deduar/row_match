import io
import pathlib
import re
from typing import List, Tuple

import pandas as pd
import pytesseract
from PIL import Image
import fitz  # PyMuPDF

from logging_config import logger

# --- Funciones para identificar y validar movimientos bancarios ---

def is_bank_transaction(line: str) -> bool:
    """
    Determina si una línea de texto corresponde a un movimiento bancario.
    
    Un movimiento bancario debe contener:
    - Una fecha en formato DD-MM-YYYY o similar
    - Una referencia numérica
    - Un concepto o descripción
    - Un monto (valor)
    - Un saldo
    
    Args:
        line: La línea de texto a evaluar
        
    Returns:
        True si la línea parece ser un movimiento bancario, False en caso contrario
    """
    # Ignorar líneas muy cortas o demasiado largas (probablemente no son movimientos)
    if len(line) < 15 or len(line) > 200:
        return False
    
    # Ignorar líneas que contienen palabras clave típicas de encabezados o información no relevante
    header_keywords = [
        "página", "page", "fecha de emisión", "rif", "cliente", "cuenta", 
        "dirección", "teléfono", "saldo anterior", "total", "subtotal", 
        "www.", ".com", "http", "consulta", "resumen", "estado de cuenta",
        "capital autorizado", "capital suscrito", "apartado postal", "mercantil",
        "banco universal", "correo", "centro de atención", "contacto", "atención",
        "digitaliza", "actualiza", "impuesto", "resumen estado", "código cliente",
        "saldo al inicio", "saldo al final", "período", "cheques", "depósitos",
        "débitos", "créditos", "oficina", "sucursal", "movimientos de cuenta"
    ]
    
    line_lower = line.lower()
    for keyword in header_keywords:
        if keyword in line_lower:
            return False
    
    # Rechazar líneas que parecen ser encabezados de tabla o información de pie de página
    if re.search(r'^(fecha|descripción|referencia|monto|importe|saldo|débito|crédito|concepto)$', 
                line_lower, re.IGNORECASE):
        return False
    
    # Rechazar líneas que contienen demasiados caracteres especiales o formatos no típicos
    # de transacciones bancarias
    special_chars = sum(1 for c in line if c in '@#$%^&*()_+=[]{}|\\:;"\'<>?')
    if special_chars > 5:  # Umbral arbitrario, ajustar según necesidad
        return False
    
    # Rechazar líneas que parecen ser información de contacto o direcciones
    if re.search(r'(tel[éf]fono|fax|correo|e-mail|@|www\.|http|https)', line_lower):
        return False
    
    # Verificar formato de fecha típico de transacciones bancarias
    # DD/MM o DD-MM seguido de año (opcional)
    date_formats = [
        r'\d{1,2}[-/]\d{1,2}(?:[-/]\d{2,4})?',  # DD/MM o DD/MM/YY o DD/MM/YYYY
        r'\d{2,4}[-/]\d{1,2}[-/]\d{1,2}'         # YYYY/MM/DD o YY/MM/DD
    ]
    
    has_date = False
    for pattern in date_formats:
        if re.search(pattern, line):
            has_date = True
            break
    
    if not has_date:
        return False
    
    # Verificar si contiene al menos un monto con formato de moneda
    # Buscamos números que pueden tener separador de miles (.) y decimal (,)
    money_patterns = [
        r'(?<!\d)(?:[\d]{1,3}(?:[.,]\d{3})+[.,]\d{2}|[\d]+[.,]\d{2})(?!\d)',  # Formato con decimales
        r'[\d.,]+\d{2}'  # Patrón más simple como respaldo
    ]
    
    has_amount = False
    for pattern in money_patterns:
        amounts = re.findall(pattern, line)
        if len(amounts) >= 1:
            has_amount = True
            break
    
    if not has_amount:
        return False
    
    # Verificar si contiene alguna referencia numérica (4+ dígitos consecutivos)
    # Buscar referencias comunes en movimientos bancarios
    ref_patterns = [
        r'\d{5,}',                 # Secuencia de 5+ dígitos (más restrictivo)
        r'[A-Z0-9]{5,}',           # Alfanumérico de 5+ caracteres (posible referencia)
        r'(?:REF|TRX|ID)[:\s]*\w+' # Palabras clave seguidas de identificadores
    ]
    
    has_ref = False
    for pattern in ref_patterns:
        if re.search(pattern, line, re.IGNORECASE):
            has_ref = True
            break
    
    if not has_ref:
        return False
    
    # Patrones específicos para identificar líneas que NO son transacciones
    non_transaction_patterns = [
        r'(?i)RIF\.?\s*[A-Z]-\d+',  # Patrón de RIF (Registro de Información Fiscal)
        r'(?i)apartado\s+postal',   # Menciones a apartado postal
        r'(?i)capital\s+(autorizado|suscrito|pagado)',  # Información de capital del banco
        r'^\s*cuenta\s+\d+\s*$',    # Solo número de cuenta en la línea
        r'(?i)^(banco|oficina|sucursal)\s*$',  # Encabezados simples
        r'(?i)^(desde|hasta)\s*$'   # Palabras sueltas de encabezados
    ]
    
    for pattern in non_transaction_patterns:
        if re.search(pattern, line):
            return False
    
    # Verificar si la línea tiene estructura de movimiento bancario
    # Un movimiento típico tiene fecha + referencia + descripción + monto + saldo
    
    # Patrón para movimientos bancarios comunes
    # Fecha (DD/MM) + número de referencia + descripción + monto
    transaction_patterns = [
        # Formato común: fecha + referencia + descripción + monto
        r'\d{1,2}[-/]\d{1,2}.*?\d{5,}.*?[\d.,]+\d{2}',
        # Formato con fecha al inicio y montos al final
        r'\d{1,2}[-/]\d{1,2}.*?[\d.,]+\d{2}.*?[\d.,]+\d{2}'
    ]
    
    for pattern in transaction_patterns:
        if re.search(pattern, line):
            return True
    
    # Si la línea tiene fecha, referencia y monto pero no coincide con los patrones anteriores,
    # hacemos una verificación adicional más estricta
    
    # Verificar si tiene un patrón de fecha seguido de número de referencia
    # Este patrón es muy común en movimientos bancarios
    date_ref_pattern = r'\d{1,2}[-/]\d{1,2}.*?\d{5,}'
    
    if re.search(date_ref_pattern, line) and has_amount:
        # Verificamos que la línea no tenga características de información general
        if not re.search(r'(?i)(capital|rif|apartado|banco universal|autorizado)', line):
            return True
    
    # Por defecto, rechazamos la línea si no ha pasado las verificaciones anteriores
    return False

def extract_transaction_data(line: str) -> Tuple[str, str, str, str, str]:
    """
    Extrae los componentes de un movimiento bancario de una línea de texto.
    
    Args:
        line: La línea de texto que contiene un movimiento bancario
        
    Returns:
        Una tupla con (fecha, referencia, concepto, monto, saldo)
    """
    # Esta es una implementación básica que se puede mejorar según los formatos específicos
    # Por ahora, simplemente devolvemos la línea completa como concepto
    
    # Extraer fecha (primera ocurrencia de DD-MM-YYYY o DD/MM/YYYY)
    date_match = re.search(r'\d{2}[-/]\d{2}[-/]\d{2,4}', line)
    date = date_match.group(0) if date_match else ""
    
    # Extraer referencia (primer número de 4+ dígitos)
    ref_match = re.search(r'\d{4,}', line)
    reference = ref_match.group(0) if ref_match else ""
    
    # Para el concepto, necesitaríamos un análisis más detallado del formato específico
    # Por ahora, usamos una aproximación simple
    concept = line
    
    # Extraer montos (últimos dos números con formato de moneda)
    amount_matches = re.findall(r'[\d.,]+\d{2}', line)
    amount = amount_matches[-2] if len(amount_matches) >= 2 else ""
    balance = amount_matches[-1] if amount_matches else ""
    
    return date, reference, concept, amount, balance

# --- Manejadores para cada tipo de archivo ---

def _handle_pdf(file_content: bytes) -> List[str]:
    """
    Extrae texto de un archivo PDF, fragmentando por líneas y filtrando solo los
    movimientos bancarios.
    """
    chunks = []
    all_lines = []
    transactions = []
    
    try:
        with fitz.open(stream=file_content, filetype="pdf") as doc:
            logger.info(f"Procesando PDF con {len(doc)} páginas.")
            for i, page in enumerate(doc):
                logger.debug(f"Extrayendo texto de la página {i+1}/{len(doc)}")
                text = page.get_text("text", sort=True) # sort=True para un orden de lectura más natural
                all_lines.extend(text.splitlines())
            logger.info("Extracción de texto del PDF completada.")
            
            # Filtrar solo las líneas que parecen ser movimientos bancarios
            for line in all_lines:
                line = line.strip()
                if line and is_bank_transaction(line):
                    transactions.append(line)
                    
                    # Opcionalmente, podemos extraer los componentes estructurados
                    # date, ref, concept, amount, balance = extract_transaction_data(line)
                    # formatted_transaction = f"Fecha: {date} | Ref: {ref} | Concepto: {concept} | Monto: {amount} | Saldo: {balance}"
                    # chunks.append(formatted_transaction)
                    
                    # Por ahora, simplemente agregamos la línea completa
                    chunks.append(line)
                    
            logger.info(f"Se identificaron {len(chunks)} movimientos bancarios de {len(all_lines)} líneas totales.")
    except Exception as e:
        logger.error(f"Error procesando el archivo PDF: {e}", exc_info=True)
        return [f"Error procesando el archivo PDF: {e}"]
    
    return chunks

def _handle_tabular(file_content: bytes, extension: str) -> List[str]:
    """
    Extrae texto de archivos tabulares (CSV, XLS, XLSX) o de tablas en HTML.
    Intenta leer el archivo como Excel y, si falla, como HTML.
    Filtra las filas para identificar solo los movimientos bancarios.
    """
    chunks = []
    all_rows = []
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
                all_rows.append(row_str)
    
    # Filtrar solo las filas que parecen ser movimientos bancarios
    transactions = []
    for row in all_rows:
        row = row.strip()
        if row and is_bank_transaction(row):
            transactions.append(row)
            chunks.append(row)
    
    logger.info(f"Se identificaron {len(chunks)} movimientos bancarios de {len(all_rows)} filas totales.")
    return chunks

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
