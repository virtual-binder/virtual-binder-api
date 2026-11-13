# Pokémon Card Scanner

Proyecto para detectar cartas Pokémon en una foto, enderezar sus recortes, leer el nombre y número mediante OCR, y consultar su ficha y precios. Incluye una API, una herramienta de línea de comandos y una app móvil.

## Estructura

- `backend/`: API FastAPI con detección OpenCV, OCR con Tesseract y consulta a TCGdex y Pokémon TCG.
- `cli/`: recortador local de cartas sin OCR ni consulta de precios.
- `mobile/`: app Android/iOS creada con Expo y React Native.
- `assets/samples/`: fotografías de prueba originales.
- `assets/debug/`: imágenes generadas durante el desarrollo del detector.

## API

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
docker build -t pokemon-card-scanner-api backend
docker run --rm -p 8000:8000 pokemon-card-scanner-api
```

### Identificar cartas

`POST /identificar` recibe un formulario multipart con el campo `archivo` (JPEG, PNG o WebP, máximo 20 MB).

```bash
curl -X POST "http://localhost:8000/identificar?incluir_recortes=false" \
  -F "archivo=@assets/samples/IMG_20261112_220900586.jpg"
```

Devuelve `total` y una lista `cartas`. Cada elemento puede incluir los datos OCR, ficha de la carta, precios, origen de los datos y avisos. Con `incluir_recortes=true`, agrega `recorte_png_base64`.

Los precios proceden de TCGplayer en USD y Cardmarket en EUR. Las fuentes externas pueden tardar o no estar disponibles; un fallo de identificación no impide obtener los recortes.

## Recortador CLI

Con el mismo entorno virtual activado:

```bash
python cli/recortar_cartas.py assets/samples/IMG_20261112_220900586.jpg \
  --salida cartas_recortadas --debug
```

Los archivos generados se guardan en `cartas_recortadas/`, carpeta excluida de Git.

## App móvil

Requisitos: una versión LTS de Node.js compatible con la versión de Expo del proyecto.

```bash
cd mobile
cp .env.example .env
npm install
npm start
```

Edita `mobile/.env` y configura `EXPO_PUBLIC_API_URL` con la URL de la API. Para probar en un teléfono conectado a la misma red, usa la IP local del equipo, por ejemplo `http://192.168.1.50:8000`; `localhost` dentro del teléfono apunta al propio teléfono.

Desde Expo CLI puedes abrir Android con `npm run android`, iOS con `npm run ios` o la versión web con `npm run web`.
