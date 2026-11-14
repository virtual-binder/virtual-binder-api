# API de identificación de cartas Pokémon
# Construcción:  docker build -t pokemon-api .
# Ejecución:     docker run -p 8000:8000 pokemon-api
FROM public.ecr.aws/awsguru/aws-lambda-adapter:1.1.0 AS lambda_adapter
FROM python:3.12-slim

COPY --from=lambda_adapter /lambda-adapter /opt/extensions/lambda-adapter
ENV AWS_LWA_READINESS_CHECK_PATH=/health
ENV AWS_LWA_READINESS_CHECK_PORT=8000
ENV PORT=8000

# Dependencias de sistema:
#   tesseract-ocr -> motor OCR (pytesseract es solo el wrapper)
#   libglib2.0-0  -> la necesita opencv-python-headless en Debian slim
RUN apt-get update \
    && apt-get install -y --no-install-recommends tesseract-ocr libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Capa separada para dependencias: si solo cambia el código, Docker reutiliza
# esta capa y no reinstala todo (builds mucho más rápidos)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY nucleo_cartas.py api.py ./

# Usuario sin privilegios: buena práctica y requerido en algunos entornos
RUN useradd --create-home appuser
USER appuser

EXPOSE 8000

# App Runner y la mayoría de servicios inyectan PORT; 8000 por defecto
CMD ["sh", "-c", "uvicorn api:app --host 0.0.0.0 --port ${PORT:-8000}"]
