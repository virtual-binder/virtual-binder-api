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
import sys

import cv2

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.nucleo_cartas import detectar_cartas, enderezar


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
