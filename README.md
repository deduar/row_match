# Row Match - Sistema de Procesamiento de Archivos y Generación de Embeddings

Este proyecto proporciona una API web construida con FastAPI para subir archivos de diversos formatos, extraer su contenido textual en fragmentos ("chunks") y generar embeddings vectoriales para cada fragmento. Todo el sistema se ejecuta dentro de un contenedor Docker para garantizar la portabilidad y facilidad de despliegue.

Este proyecto fue generado por un agente de IA siguiendo un plan predefinido.

## Prerrequisitos

Asegúrate de tener instalados los siguientes componentes en tu sistema:

-   [Docker](https://docs.docker.com/get-docker/)
-   [Docker Compose](https://docs.docker.com/compose/install/) (generalmente incluido con Docker Desktop)

## Estructura del Proyecto

```
.
├── Dockerfile
├── docker-compose.yml
├── embeddings.py
├── main.py
├── PLAN.md
├── processing.py
└── requirements.txt
```

-   **`Dockerfile`**: Define la imagen del contenedor, incluyendo el entorno virtual y las dependencias.
-   **`docker-compose.yml`**: Orquesta la construcción y ejecución del contenedor de la API.
-   **`main.py`**: El punto de entrada de la API FastAPI.
-   **`processing.py`**: Lógica para la extracción de texto de los diferentes tipos de archivo.
-   **`embeddings.py`**: Lógica para la generación de los embeddings.
-   **`requirements.txt`**: Lista de las dependencias de Python.
-   **`PLAN.md`**: Documento con el plan de implementación seguido.

## Cómo Ejecutar el Proyecto

1.  **Construye y levanta el contenedor con Docker Compose.**
    Abre una terminal en el directorio raíz del proyecto y ejecuta el siguiente comando:

    ```bash
    docker-compose up --build
    ```
    La primera vez que ejecutes este comando, Docker descargará la imagen base de Python, instalará las dependencias del sistema y de Python, y construirá la imagen de tu aplicación. Esto puede tardar varios minutos, especialmente por la descarga de los modelos de `sentence-transformers`. Las ejecuciones posteriores serán mucho más rápidas.

2.  **Verifica que el servicio esté funcionando.**
    Una vez que el contenedor esté en ejecución, puedes abrir tu navegador y visitar [http://localhost:8000](http://localhost:8000). Deberías ver el mensaje de bienvenida: `{"message":"Bienvenido a la API de procesamiento de archivos. Visita /docs para la documentación interactiva."}`.

## Cómo Usar la API

Puedes interactuar con la API a través de la documentación interactiva de Swagger UI o enviando una petición `curl`.

### Usando la Documentación Interactiva (Swagger)

1.  Abre tu navegador y ve a [http://localhost:8000/docs](http://localhost:8000/docs).
2.  Expande el endpoint `POST /process-file/`.
3.  Haz clic en "Try it out".
4.  Haz clic en "Choose File" y selecciona el archivo que deseas procesar.
5.  Haz clic en "Execute".

La respuesta aparecerá en la misma página.

### Usando `curl`

Abre una terminal y ejecuta el siguiente comando, reemplazando `path/to/your/file.pdf` con la ruta real de tu archivo.

**Ejemplo con un archivo PDF:**
```bash
curl -X 'POST' \
  'http://localhost:8000/process-file/' \
  -H 'accept: application/json' \
  -H 'Content-Type: multipart/form-data' \
  -F 'file=@/path/to/your/file.pdf'
```

**Ejemplo con un archivo de texto:**
```bash
curl -X 'POST' \
  'http://localhost:8000/process-file/' \
  -H 'accept: application/json' \
  -H 'Content-Type: multipart/form-data' \
  -F 'file=@/path/to/your/notes.txt'
```

La respuesta será un objeto JSON con el nombre del archivo y una lista de los fragmentos de texto junto con sus embeddings correspondientes.
