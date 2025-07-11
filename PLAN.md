# Plan de Implementación: Sistema de Procesamiento de Archivos y Generación de Embeddings

## 1. Objetivo del Proyecto

Crear un servicio web, contenido en un entorno de Docker, que permita a un usuario subir un archivo en múltiples formatos (PDF, XLS, CSV, imágenes, etc.). El sistema deberá leer el archivo, extraer su contenido en fragmentos de texto ("chunks") y devolver una lista de los embeddings vectoriales correspondientes a cada fragmento.

El proyecto se ejecutará dentro de un virtual environment de Python (`.venv`) para un manejo de dependencias limpio y aislado.

## 2. Tecnologías Propuestas

-   **Lenguaje**: Python 3.10+
-   **Framework de API**: **FastAPI** - Por su alto rendimiento, facilidad de uso y generación automática de documentación.
-   **Generación de Embeddings**: **`sentence-transformers`** - Una librería de vanguardia para obtener embeddings de texto de alta calidad. Se usará el modelo `all-MiniLM-L6-v2` por su balance entre rendimiento y eficiencia.
-   **Procesamiento de Archivos**:
    -   **PDF**: `PyMuPDF` - Rápido y preciso para la extracción de texto.
    -   **Excel (XLS, XLSX) y CSV**: `pandas` - La librería estándar para manipulación de datos tabulares.
    -   **Imágenes (PNG, GIF, JPG)**: `pytesseract` y `Pillow` - Para realizar OCR (Reconocimiento Óptico de Caracteres) y extraer texto de imágenes.
    -   **Texto Plano**: Librerías estándar de Python.
-   **Contenerización**: **Docker** y **Docker Compose** - Para crear un entorno de desarrollo y producción reproducible y aislado.

## 3. Arquitectura del Sistema

La arquitectura será modular para facilitar el mantenimiento y la escalabilidad.

-   **Punto de Entrada (`main.py`)**:
    -   Define el endpoint de la API `POST /process-file/`.
    -   Recibe el archivo subido por el usuario.
    -   Orquesta el llamado a los módulos de procesamiento y embeddings.
-   **Módulo de Procesamiento (`processing.py`)**:
    -   Contiene la lógica para identificar el tipo de archivo (basado en su extensión o tipo MIME).
    -   Delega la extracción de texto al manejador ("handler") correspondiente.
    -   Implementa la lógica de "chunking" (división del texto en fragmentos).
-   **Módulo de Embeddings (`embeddings.py`)**:
    -   Recibe una lista de fragmentos de texto.
    -   Utiliza el modelo de `sentence-transformers` para convertir cada fragmento en un vector de embedding.
    -   Retorna la lista de embeddings.
-   **Base de Datos**:
    -   Para esta fase inicial, **no se requiere una base de datos**. El servicio procesará el archivo y devolverá los embeddings directamente en la respuesta de la API. Si en el futuro se necesita persistencia o búsqueda, se podría añadir una base de datos vectorial (ej. ChromaDB, Weaviate) en su propio contenedor.

## 4. Flujo de Contenerización con Docker

-   **`Dockerfile`**:
    1.  Utilizará una imagen oficial de Python como base.
    2.  Instalará las dependencias del sistema operativo necesarias (como `tesseract-ocr`).
    3.  Creará un directorio de trabajo y un virtual environment (`.venv`).
    4.  Copiará el archivo `requirements.txt` y instalará las dependencias de Python dentro del `.venv`.
    5.  Copiará el resto del código fuente de la aplicación.
    6.  Expondrá el puerto del servidor y definirá el comando para ejecutar la aplicación FastAPI con Uvicorn.
-   **`docker-compose.yml`**:
    -   Definirá un único servicio (`app`) que construirá la imagen a partir del `Dockerfile`.
    -   Gestionará el mapeo de puertos entre el host y el contenedor.
    -   Facilitará el levantamiento de todo el entorno con un solo comando (`docker-compose up`).

## 5. Pasos de Implementación

1.  **Crear `requirements.txt`**: Listar todas las dependencias de Python.
2.  **Implementar el Código de la Aplicación**: Escribir los módulos `main.py`, `processing.py` y `embeddings.py`.
3.  **Crear el `Dockerfile`**: Definir la imagen del contenedor de la aplicación.
4.  **Crear `docker-compose.yml`**: Orquestar el servicio de la aplicación.
5.  **Proveer Instrucciones de Uso**: Crear un `README.md` (o añadir a este) con los pasos para construir y ejecutar el proyecto.
