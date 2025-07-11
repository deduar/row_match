# Usar una imagen de Python 3.10 como base
FROM python:3.10-slim

# Establecer el directorio de trabajo
WORKDIR /app

# Copiar el archivo de requerimientos e instalar las dependencias
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el resto del código de la aplicación
COPY . .

# Exponer el puerto por defecto de Streamlit
EXPOSE 8501

# El comando para ejecutar la aplicación de Streamlit
# --server.address=0.0.0.0 permite que sea accesible desde fuera del contenedor
# --server.port=8501 es el puerto estándar
CMD ["streamlit", "run", "app.py", "--server.address=0.0.0.0", "--server.port=8501"]
