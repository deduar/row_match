# --- Fase 1: Construcción y Dependencias ---

# Usar una imagen de Python 3.10 como base. La versión "slim" es más ligera.
FROM python:3.10-slim as builder

# Establecer el directorio de trabajo dentro del contenedor
WORKDIR /app

# Instalar dependencias del sistema operativo requeridas por las librerías de Python
# - tesseract-ocr: Motor de OCR para pytesseract
# - libgl1-mesa-glx: Dependencia de OpenCV
# - curl: Necesario para el healthcheck en docker-compose
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    libgl1-mesa-glx \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Crear un entorno virtual para aislar las dependencias del proyecto
ENV VIRTUAL_ENV=/app/.venv
RUN python3 -m venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

# Copiar el archivo de requerimientos primero para aprovechar el cache de Docker
COPY requirements.txt .

# Instalar las dependencias de Python dentro del entorno virtual
RUN pip install --no-cache-dir -r requirements.txt


# --- Fase 2: Imagen Final ---

# Usar una imagen base limpia para la imagen final, para reducir su tamaño
FROM python:3.10-slim

# Establecer el directorio de trabajo
WORKDIR /app

# Instalar solo las dependencias de sistema necesarias para la ejecución
# Incluyendo curl para el healthcheck
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    libgl1-mesa-glx \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copiar el entorno virtual con las dependencias ya instaladas desde la fase de construcción
COPY --from=builder /app/.venv ./.venv

# Copiar el código fuente de la aplicación
COPY . .

# Activar el entorno virtual para los comandos subsiguientes
ENV PATH="/app/.venv/bin:$PATH"

# Exponer el puerto en el que se ejecutará la aplicación
EXPOSE 8000

# Comando para ejecutar la aplicación usando Uvicorn
# --host 0.0.0.0 permite que el servidor sea accesible desde fuera del contenedor
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]