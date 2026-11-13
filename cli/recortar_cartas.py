#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Detector y recortador de cartas Pokémon en fotos.

Detecta cartas (rectángulos con la proporción de una carta: 63 x 88 mm),
corrige su perspectiva y guarda cada carta recortada como imagen individual.

Uso:
    python cli/recortar_cartas.py foto.jpg
    python cli/recortar_cartas.py foto.jpg -o salida/ --ancho 744 --debug
"""

import argparse
import os
import cv2
import numpy as np

# Proporción real de una carta Pokémon: 63 mm de ancho x 88 mm de alto
PROPORCION_CARTA = 63 / 88          # ancho / alto
PROPORCION_MIN, PROPORCION_MAX = 0.45, 0.90  # rango admisible (holgado por perspectiva)
AREA_MINIMA_FRAC = 0.02             # la carta debe ocupar al menos 2% de la foto
MARGEN_BORDE_FRAC = 0.02            # para descartar el propio borde de la foto


def ordenar_puntos(pts):
    """Ordena 4 puntos como: sup-izq, sup-der, inf-der, inf-izq."""
    pts = pts.reshape(4, 2).astype("float32")
    s = pts.sum(axis=1)
    d = np.diff(pts, axis=1).ravel()
    return np.array([
        pts[np.argmin(s)],   # sup-izq
        pts[np.argmin(d)],   # sup-der
        pts[np.argmax(s)],   # inf-der
        pts[np.argmax(d)],   # inf-izq
    ], dtype="float32")


def enderezar(imagen, pts, ancho_salida):
    """Aplica transformación de perspectiva para dejar la carta 'de frente'."""
    rect = ordenar_puntos(pts)
    alto_salida = int(round(ancho_salida / PROPORCION_CARTA))
    destino = np.array([
        [0, 0],
        [ancho_salida - 1, 0],
        [ancho_salida - 1, alto_salida - 1],
        [0, alto_salida - 1],
    ], dtype="float32")
    M = cv2.getPerspectiveTransform(rect, destino)
    return cv2.warpPerspective(imagen, M, (ancho_salida, alto_salida))


def es_proporcion_valida(quad):
    """Proporción cercana a la de una carta, con holgura por la perspectiva."""
    rect = ordenar_puntos(quad)
    (tl, tr, br, bl) = rect
    ancho = max(np.linalg.norm(tr - tl), np.linalg.norm(br - bl))
    alto = max(np.linalg.norm(bl - tl), np.linalg.norm(br - tr))
    if min(ancho, alto) <= 0:
        return False
    proporcion = min(ancho, alto) / max(ancho, alto)
    return PROPORCION_MIN <= proporcion <= PROPORCION_MAX


def es_borde_de_foto(quad, forma_imagen):
    """Descarta el contorno formado por el propio marco de la imagen."""
    alto_img, ancho_img = forma_imagen[:2]
    margen_x, margen_y = ancho_img * MARGEN_BORDE_FRAC, alto_img * MARGEN_BORDE_FRAC
    esquinas_img = [(0, 0), (ancho_img, 0), (ancho_img, alto_img), (0, alto_img)]
    for ex, ey in esquinas_img:
        if not any(abs(p[0] - ex) < margen_x and abs(p[1] - ey) < margen_y
                   for p in quad):
            return False
    return True


def detectar_cartas(imagen):
    """Devuelve la lista de cuadriláteros (4x2) que parecen cartas."""
    area_min = AREA_MINIMA_FRAC * imagen.shape[0] * imagen.shape[1]

    gris = cv2.cvtColor(imagen, cv2.COLOR_BGR2GRAY)
    gris = cv2.GaussianBlur(gris, (5, 5), 0)

    # Umbral adaptativo: funciona con distintos fondos e iluminación
    binaria = cv2.adaptiveThreshold(
        gris, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 25, 10)
    binaria = cv2.morphologyEx(binaria, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))

    # También detectamos bordes para cartas que se confunden con el fondo
    bordes = cv2.Canny(gris, 30, 90)
    bordes = cv2.dilate(bordes, np.ones((3, 3), np.uint8), iterations=2)

    quads = []
    for mascara in (binaria, bordes):
        contornos, _ = cv2.findContours(
            mascara, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        for c in contornos:
            if cv2.contourArea(c) < area_min:
                continue
            peri = cv2.arcLength(c, True)
            aprox = cv2.approxPolyDP(c, 0.02 * peri, True)
            if len(aprox) == 4 and cv2.isContourConvex(aprox):
                q = ordenar_puntos(aprox)
                if es_proporcion_valida(q) and not es_borde_de_foto(q, imagen.shape):
                    quads.append(q)

    # Eliminar duplicados (la misma carta detectada dos veces)
    unicas = []
    for q in quads:
        centro = q.mean(axis=0)
        if not any(np.linalg.norm(centro - u.mean(axis=0)) < 20 for u in unicas):
            unicas.append(q)
    return unicas


def main():
    ap = argparse.ArgumentParser(
        description="Identifica y recorta cartas Pokémon de una foto.")
    ap.add_argument("imagen", help="Ruta de la foto con las cartas")
    ap.add_argument("-o", "--salida", default="cartas_recortadas",
                    help="Carpeta de salida (por defecto: cartas_recortadas)")
    ap.add_argument("--ancho", type=int, default=744,
                    help="Ancho en píxeles de cada carta recortada (744 px = 300 dpi)")
    ap.add_argument("--debug", action="store_true",
                    help="Guarda una imagen con los contornos detectados dibujados")
    args = ap.parse_args()

    imagen = cv2.imread(args.imagen)
    if imagen is None:
        raise SystemExit(f"No se pudo abrir la imagen: {args.imagen}")

    os.makedirs(args.salida, exist_ok=True)
    quads = detectar_cartas(imagen)

    if not quads:
        print("No se detectaron cartas. Prueba con mejor iluminación,")
        print("un fondo liso que contraste, o ejecuta con --debug para revisar.")
        return

    print(f"Se detectaron {len(quads)} carta(s).")

    for i, quad in enumerate(quads, 1):
        carta = enderezar(imagen, quad, args.ancho)
        ruta = os.path.join(args.salida, f"carta_{i:02d}.png")
        cv2.imwrite(ruta, carta)
        print(f"  Guardada: {ruta}")

    if args.debug:
        vista = imagen.copy()
        for i, q in enumerate(quads, 1):
            cv2.polylines(vista, [q.astype(int)], True, (0, 255, 0), 4)
            cv2.putText(vista, str(i), tuple(q[0].astype(int) + [10, 40]),
                        cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 255, 0), 3)
        ruta_dbg = os.path.join(args.salida, "debug_deteccion.jpg")
        cv2.imwrite(ruta_dbg, vista)
        print(f"  Imagen de depuración: {ruta_dbg}")


if __name__ == "__main__":
    main()
