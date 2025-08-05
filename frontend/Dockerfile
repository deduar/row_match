# Usar una imagen de Python 3.10 como base
FROM python:3.10-slim

# Establecer el directorio de trabajo
WORKDIR /app/frontend

# Instalar dependencias del sistema necesarias
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copiar el archivo de requerimientos e instalar las dependencias
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Crear directorio para configuración de Streamlit
RUN mkdir -p .streamlit

# Copiar la configuración de Streamlit
COPY .streamlit/config.toml .streamlit/

# Copiar el resto del código de la aplicación
# En desarrollo, esto será sobrescrito por volúmenes
COPY . .

# Exponer el puerto por defecto de Streamlit
EXPOSE 8501

# El comando para ejecutar la aplicación de Streamlit con hot-reload
# --server.address=0.0.0.0 permite que sea accesible desde fuera del contenedor
# --server.port=8501 es el puerto estándar
# --server.runOnSave=true habilita el auto-reload cuando hay cambios
# --server.headless=true ejecuta en modo headless para contenedores
CMD ["streamlit", "run", "app.py", "--server.address=0.0.0.0", "--server.port=8501", "--server.runOnSave=true", "--server.headless=true"]
