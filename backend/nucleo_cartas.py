#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Núcleo: detección, recorte, OCR e identificación de cartas Pokémon con precios.

Pensado para ser importado por un backend (api.py) o usado desde otro script:

    from nucleo_cartas import procesar_foto
    with open("foto.jpg", "rb") as f:
        resultado = procesar_foto(f.read())
"""

import re
import base64
import requests
import cv2
import numpy as np
import pytesseract

# ---------- Configuración ----------

PROPORCION_CARTA = 63 / 88                     # ancho / alto de una carta real
PROPORCION_MIN, PROPORCION_MAX = 0.45, 0.90    # rango admisible (perspectiva)
AREA_MINIMA_FRAC = 0.02
MARGEN_BORDE_FRAC = 0.02

TCGDEX = "https://api.tcgdex.net/v2/en"
POKEMONTCG = "https://api.pokemontcg.io/v2"
HTTP_TIMEOUT = 20

_cache_detalle = {}   # caché en memoria: id de carta -> detalle con precios


# ---------- Detección y recorte (igual que en el recortador CLI) ----------

def ordenar_puntos(pts):
    """Ordena 4 puntos como: sup-izq, sup-der, inf-der, inf-izq."""
    pts = pts.reshape(4, 2).astype("float32")
    s = pts.sum(axis=1)
    d = np.diff(pts, axis=1).ravel()
    return np.array([
        pts[np.argmin(s)], pts[np.argmin(d)],
        pts[np.argmax(s)], pts[np.argmax(d)],
    ], dtype="float32")


def enderezar(imagen, pts, ancho_salida):
    """Transformación de perspectiva: deja la carta de frente."""
    rect = ordenar_puntos(pts)
    alto_salida = int(round(ancho_salida / PROPORCION_CARTA))
    destino = np.array([
        [0, 0], [ancho_salida - 1, 0],
        [ancho_salida - 1, alto_salida - 1], [0, alto_salida - 1],
    ], dtype="float32")
    M = cv2.getPerspectiveTransform(rect, destino)
    return cv2.warpPerspective(imagen, M, (ancho_salida, alto_salida))


def es_proporcion_valida(quad):
    rect = ordenar_puntos(quad)
    (tl, tr, br, bl) = rect
    ancho = max(np.linalg.norm(tr - tl), np.linalg.norm(br - bl))
    alto = max(np.linalg.norm(bl - tl), np.linalg.norm(br - tr))
    if min(ancho, alto) <= 0:
        return False
    return PROPORCION_MIN <= min(ancho, alto) / max(ancho, alto) <= PROPORCION_MAX


def es_borde_de_foto(quad, forma_imagen):
    """Descarta el contorno formado por el propio marco de la imagen."""
    alto_img, ancho_img = forma_imagen[:2]
    mx, my = ancho_img * MARGEN_BORDE_FRAC, alto_img * MARGEN_BORDE_FRAC
    for ex, ey in [(0, 0), (ancho_img, 0), (ancho_img, alto_img), (0, alto_img)]:
        if not any(abs(p[0] - ex) < mx and abs(p[1] - ey) < my for p in quad):
            return False
    return True


def detectar_cartas(imagen):
    """Devuelve la lista de cuadriláteros (4x2) que parecen cartas."""
    area_min = AREA_MINIMA_FRAC * imagen.shape[0] * imagen.shape[1]
    gris = cv2.cvtColor(imagen, cv2.COLOR_BGR2GRAY)
    gris = cv2.GaussianBlur(gris, (5, 5), 0)

    binaria = cv2.adaptiveThreshold(
        gris, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 25, 10)
    binaria = cv2.morphologyEx(binaria, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
    bordes = cv2.Canny(gris, 30, 90)
    bordes = cv2.dilate(bordes, np.ones((3, 3), np.uint8), iterations=2)

    quads = []
    for mascara in (binaria, bordes):
        contornos, _ = cv2.findContours(
            mascara, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        for c in contornos:
            if cv2.contourArea(c) < area_min:
                continue
            aprox = cv2.approxPolyDP(c, 0.02 * cv2.arcLength(c, True), True)
            if len(aprox) == 4 and cv2.isContourConvex(aprox):
                q = ordenar_puntos(aprox)
                if es_proporcion_valida(q) and not es_borde_de_foto(q, imagen.shape):
                    quads.append(q)

    unicas = []
    for q in quads:
        centro = q.mean(axis=0)
        if not any(np.linalg.norm(centro - u.mean(axis=0)) < 20 for u in unicas):
            unicas.append(q)
    return unicas


# ---------- OCR: nombre y número de coleccionista ----------

def _variantes_ocr(region, escala=3):
    """Genera varias versiones de la zona (gris, Otsu, adaptativo; ±invertir).

    Tesseract se comporta de forma muy distinta según el fondo de la carta
    (texto negro sobre amarillo, blanco sobre oscuro, holográficas...),
    así que se prueban todas y se elige la lectura más convincente.
    """
    grande = cv2.resize(region, None, fx=escala, fy=escala,
                        interpolation=cv2.INTER_CUBIC)
    gris = cv2.cvtColor(grande, cv2.COLOR_BGR2GRAY)
    base = [
        gris,
        cv2.threshold(gris, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1],
        cv2.adaptiveThreshold(gris, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                              cv2.THRESH_BINARY, 41, 20),
    ]
    variantes = []
    for im in base:
        for inv in (False, True):
            v = cv2.bitwise_not(im) if inv else im
            # margen blanco: tesseract lee mejor con aire alrededor del texto
            variantes.append(cv2.copyMakeBorder(
                v, 25, 25, 25, 25, cv2.BORDER_CONSTANT, value=255))
    return variantes


def _ocr_linea(imagen, whitelist=None):
    config = "--psm 7"   # tratar la imagen como una sola línea de texto
    if whitelist:
        config += f" -c tessedit_char_whitelist={whitelist}"
    return pytesseract.image_to_string(imagen, config=config).strip()


def leer_nombre(carta):
    """Lee el nombre en la franja superior de la carta."""
    h, w = carta.shape[:2]
    zona = carta[int(h * 0.03):int(h * 0.11), int(w * 0.06):int(w * 0.62)]
    mejor = ""
    for v in _variantes_ocr(zona):
        texto = _ocr_linea(v)
        limpio = re.sub(r"[^A-Za-zÀ-ÿ\u2642\u2640\u03b4 .'-]", " ", texto)
        limpio = re.sub(r"\s+", " ", limpio).strip()
        # quedarse con la lectura con más letras (señal de lectura completa)
        if sum(c.isalpha() for c in limpio) > sum(c.isalpha() for c in mejor):
            mejor = limpio
    return mejor if sum(c.isalpha() for c in mejor) >= 3 else ""


def leer_numero(carta):
    """Lee el número de coleccionista (ej. 4/102) en la franja inferior.

    Según la expansión aparece abajo a la izquierda o a la derecha,
    así que se prueban ambas esquinas y todas las variantes de imagen.
    """
    h, w = carta.shape[:2]
    franja_y = slice(int(h * 0.93), h)
    for franja_x in (slice(0, int(w * 0.38)), slice(int(w * 0.62), w)):
        zona = carta[franja_y, franja_x]
        for v in _variantes_ocr(zona, escala=4):
            texto = _ocr_linea(v, whitelist="0123456789/")
            m = re.search(r"(\d{1,3})\s*/\s*(\d{1,3})", texto)
            if m:
                return m.group(1), m.group(2)          # (número, total del set)
            m = re.fullmatch(r"(\d{1,3})", texto.replace(" ", ""))
            if m:
                return m.group(1), None
    return None, None


# ---------- Identificación y precios ----------

def _detalle_tcgdex(id_carta):
    if id_carta not in _cache_detalle:
        r = requests.get(f"{TCGDEX}/cards/{id_carta}", timeout=HTTP_TIMEOUT)
        r.raise_for_status()
        _cache_detalle[id_carta] = r.json()
    return _cache_detalle[id_carta]


def _buscar_tcgdex(nombre, numero):
    params = {"name": f"like:{nombre}"}
    if numero:
        params["localId"] = numero.lstrip("0") or "0"
    r = requests.get(f"{TCGDEX}/cards", params=params, timeout=HTTP_TIMEOUT)
    r.raise_for_status()
    candidatos = r.json()
    if not candidatos:
        return None
    # Preferir coincidencia exacta de nombre sobre "contiene"
    for c in candidatos:
        if c["name"].lower() == nombre.lower():
            return _detalle_tcgdex(c["id"])
    return _detalle_tcgdex(candidatos[0]["id"])


def _buscar_pokemontcg(nombre, numero):
    q = f'name:"{nombre}"'
    if numero:
        q += f" number:{numero.lstrip('0') or '0'}"
    r = requests.get(f"{POKEMONTCG}/cards",
                     params={"q": q, "pageSize": 5}, timeout=HTTP_TIMEOUT)
    r.raise_for_status()
    data = r.json().get("data", [])
    return data[0] if data else None


def _precios_desde_tcgdex(d):
    """Normaliza los precios de TCGdex a un formato común."""
    cm, tp = d.get("pricing", {}).get("cardmarket", {}), d.get("pricing", {}).get("tcgplayer", {})
    precios = {"cardmarket_eur": None, "tcgplayer_usd": None}
    if cm:
        precios["cardmarket_eur"] = {
            "tendencia": cm.get("trend"), "media": cm.get("avg"),
            "tendencia_holo": cm.get("trend-holo"),
            "actualizado": cm.get("updated"),
        }
    if tp:
        por_acabado = {}
        for acabado in ("normal", "holofoil", "reverseHolofoil"):
            if tp.get(acabado) and tp[acabado].get("marketPrice") is not None:
                por_acabado[acabado] = tp[acabado]["marketPrice"]
        if por_acabado:
            precios["tcgplayer_usd"] = {
                "por_acabado": por_acabado, "actualizado": tp.get("updated")}
    return precios


def _precios_desde_pokemontcg(d):
    """Normaliza los precios de pokemontcg.io al mismo formato."""
    precios = {"cardmarket_eur": None, "tcgplayer_usd": None}
    cm = d.get("cardmarket", {}).get("prices", {})
    if cm:
        precios["cardmarket_eur"] = {
            "tendencia": cm.get("trendPrice"), "media": cm.get("averageSellPrice"),
            "tendencia_holo": cm.get("trendPrice"),  # cardmarket no separa aquí
            "actualizado": d.get("cardmarket", {}).get("updatedAt"),
        }
    tp = d.get("tcgplayer", {}).get("prices", {})
    por_acabado = {}
    for clave, destino in (("normal", "normal"), ("holofoil", "holofoil"),
                           ("reverseHolofoil", "reverseHolofoil")):
        if tp.get(clave) and tp[clave].get("market") is not None:
            por_acabado[destino] = tp[clave]["market"]
    if por_acabado:
        precios["tcgplayer_usd"] = {
            "por_acabado": por_acabado,
            "actualizado": d.get("tcgplayer", {}).get("updatedAt")}
    return precios


def identificar_carta(nombre_ocr, numero_ocr):
    """Busca la carta por nombre + número y devuelve ficha + precios.

    Fuente principal: TCGdex (gratuita, sin clave).
    Respaldo: pokemontcg.io, por si la principal falla.
    """
    if not nombre_ocr:
        return None, "OCR no pudo leer el nombre; imposible buscar la carta."

    aviso_numero = None
    if not numero_ocr:
        aviso_numero = ("No se leyó el número de coleccionista: se devuelve la "
                        "primera coincidencia por nombre, que puede ser de otra "
                        "expansión. Revisar manualmente.")

    errores = []
    for buscar, extraer, origen in (
            (_buscar_tcgdex, _precios_desde_tcgdex, "tcgdex"),
            (_buscar_pokemontcg, _precios_desde_pokemontcg, "pokemontcg")):
        try:
            d = buscar(nombre_ocr, numero_ocr)
            if not d:
                errores.append(f"{origen}: sin resultados")
                continue
            if origen == "tcgdex":
                ficha = {
                    "id": d["id"], "nombre": d["name"],
                    "expansion": d["set"]["name"],
                    "numero": d.get("localId"),
                    "rareza": d.get("rarity"),
                    "imagen": (d.get("image") or "") + "/high.png",
                }
            else:
                ficha = {
                    "id": d["id"], "nombre": d["name"],
                    "expansion": d["set"]["name"],
                    "numero": d.get("number"),
                    "rareza": d.get("rarity"),
                    "imagen": d.get("images", {}).get("large"),
                }
            aviso = aviso_numero
            if numero_ocr and ficha["numero"] and \
                    ficha["numero"].lstrip("0") != str(numero_ocr).lstrip("0"):
                aviso = ("El número leído por OCR no coincide con el de la "
                         "carta encontrada; revisar manualmente.")
            return {"origen": origen, "carta": ficha,
                    "precios": extraer(d)}, aviso
        except Exception as e:
            errores.append(f"{origen}: {e}")
    return None, "; ".join(errores) or "Carta no encontrada en ninguna fuente."


# ---------- Pipeline completo ----------

def procesar_foto(imagen_bytes, ancho_carta=744, incluir_recortes=False):
    """Detecta, recorta, lee e identifica todas las cartas de una foto.

    Recibe los bytes de la imagen y devuelve un dict con la lista de cartas.
    """
    arr = np.frombuffer(imagen_bytes, np.uint8)
    imagen = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if imagen is None:
        raise ValueError("No se pudo decodificar la imagen.")

    resultado = {"cartas": [], "total": 0}
    for quad in detectar_cartas(imagen):
        recorte = enderezar(imagen, quad, ancho_carta)
        nombre = leer_nombre(recorte)
        numero, total_set = leer_numero(recorte)

        item = {"ocr": {"nombre": nombre, "numero": numero,
                        "total_set": total_set},
                "carta": None, "precios": None, "aviso": None}

        ident, aviso = identificar_carta(nombre, numero)
        if ident:
            item.update(ident)
        if aviso:
            item["aviso"] = aviso

        if incluir_recortes:
            ok, png = cv2.imencode(".png", recorte)
            item["recorte_png_base64"] = base64.b64encode(png).decode() if ok else None

        resultado["cartas"].append(item)

    resultado["total"] = len(resultado["cartas"])
    return resultado
