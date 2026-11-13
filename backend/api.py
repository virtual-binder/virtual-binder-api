#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API backend para identificar cartas Pokémon y obtener su precio.

Arranque:
    uvicorn api:app --host 0.0.0.0 --port 8000

Endpoint principal:
    POST /identificar   (multipart, campo "archivo" con la foto)

Documentación interactiva automática en:  http://localhost:8000/docs
"""

import os

from fastapi import FastAPI, File, Query, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from nucleo_cartas import procesar_foto

app = FastAPI(
    title="Identificador de cartas Pokémon",
    description=("Detecta y recorta las cartas de una foto, lee nombre y "
                 "número por OCR y devuelve la ficha y el precio de mercado "
                 "(TCGplayer en USD y Cardmarket en EUR)."),
    version="1.0.0",
)

cors_origins = os.getenv(
    "CORS_ORIGINS",
    "http://localhost:3000,http://localhost:8081",
).split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in cors_origins if origin.strip()],
    allow_methods=["*"],
    allow_headers=["*"],
)

TIPOS_PERMITIDOS = {"image/jpeg", "image/png", "image/webp"}
TAMANO_MAX = 20 * 1024 * 1024   # 20 MB


@app.get("/health")
def health():
    return {"estado": "ok"}


@app.post("/identificar")
async def identificar(
    archivo: UploadFile = File(..., description="Foto con una o varias cartas"),
    ancho_carta: int = Query(744, ge=200, le=2000,
                             description="Ancho en px del recorte enderezado"),
    incluir_recortes: bool = Query(
        False, description="Incluir cada recorte en base64 en la respuesta"),
):
    if archivo.content_type not in TIPOS_PERMITIDOS:
        raise HTTPException(415, f"Tipo no soportado: {archivo.content_type}. "
                                 f"Usa JPEG, PNG o WebP.")

    datos = await archivo.read()
    if len(datos) > TAMANO_MAX:
        raise HTTPException(413, "La imagen supera el máximo de 20 MB.")

    try:
        resultado = procesar_foto(datos, ancho_carta=ancho_carta,
                                  incluir_recortes=incluir_recortes)
    except ValueError as e:
        raise HTTPException(422, str(e))

    if resultado["total"] == 0:
        resultado["aviso"] = ("No se detectaron cartas. Prueba con fondo liso, "
                              "buena luz y las cartas sin solaparse.")
    return JSONResponse(resultado)
