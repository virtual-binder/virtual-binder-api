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

Comprueba el servicio en `http://localhost:8000/salud` y abre su documentación en `http://localhost:8000/docs`.

También puedes usar Docker:

```bash
docker build -t virtual-binder-api backend
docker run --rm -p 8000:8000 virtual-binder-api
```

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
