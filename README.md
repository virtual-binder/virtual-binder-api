# Virtual Binder API

Backend de Virtual Binder. Actualmente detecta cartas Pokémon en una foto, endereza sus recortes, lee el nombre y número mediante OCR y consulta su ficha y precios.

## Estructura

- `backend/`: API FastAPI con detección OpenCV, OCR con Tesseract y consulta a TCGdex y Pokémon TCG.
- `cli/`: recortador local de cartas sin OCR ni consulta de precios.
- `assets/samples/`: fotografías de prueba originales.
- `assets/debug/`: imágenes generadas durante el desarrollo del detector.

## Ejecutar la API

Requisitos: Python 3.12 o superior y Tesseract OCR.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
uvicorn api:app --app-dir backend --host 0.0.0.0 --port 8000 --reload
```

Comprueba el servicio en `http://localhost:8000/health` y abre su documentación en `http://localhost:8000/docs`.

CORS permite por defecto `http://localhost:3000` y `http://localhost:8081`. Configura `CORS_ORIGINS` con una lista separada por comas para otros entornos. Desde `virtual-binder-infra`, `make up` levanta esta API y PostgreSQL mediante Docker Compose.

También puedes usar Docker:

```bash
docker build -t virtual-binder-api backend
docker run --rm -p 8000:8000 virtual-binder-api
```

## Publicación

`.github/workflows/publish-api.yml` construye el contenedor, comprueba `/health`, procesa una foto real y publica la imagen en Artifact Registry. Después solicita el despliegue protegido en `virtual-binder-infra`.

Configura las variables `GCP_PROJECT_ID`, `GCP_REGION`, `GCP_API_SERVICE_ACCOUNT` y `GCP_WORKLOAD_IDENTITY_PROVIDER`. Para la llamada entre repositorios, agrega los secretos `INFRA_DISPATCH_APP_ID` y `INFRA_DISPATCH_PRIVATE_KEY` de una GitHub App con acceso limitado a `virtual-binder-infra` y permiso `Contents: write`.

## Identificar cartas

`POST /identificar` recibe un formulario multipart con el campo `archivo` (JPEG, PNG o WebP, máximo 20 MB).

```bash
curl -X POST "http://localhost:8000/identificar?incluir_recortes=false" \
  -F "archivo=@assets/samples/IMG_20261112_220900586.jpg"
```

Devuelve `total` y una lista `cartas`. Cada elemento puede incluir los datos OCR, ficha de la carta, precios, origen de los datos y avisos. Con `incluir_recortes=true`, agrega `recorte_png_base64`.

Los precios proceden de TCGplayer en USD y Cardmarket en EUR. Las fuentes externas pueden tardar o no estar disponibles; un fallo de identificación no impide obtener los recortes.

## Recortador CLI

```bash
python cli/recortar_cartas.py assets/samples/IMG_20261112_220900586.jpg \
  --salida cartas_recortadas --debug
```

Los archivos generados se guardan en `cartas_recortadas/`, carpeta excluida de Git.
