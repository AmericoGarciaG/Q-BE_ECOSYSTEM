# Q-BE Casino Deportes — OCR Parser Engine (src/ingestion/ocr_parser.py)
"""
[ARCH-PILLAR] Sensor de Ingesta por Visión y OCR: Caliente.mx OCR Parser.
[GOVERNANCE-01] Auto-detección en Windows, preprocesamiento con Pillow y extracción
estructurada de cuotas 1X2, torneos y Pago Anticipado. Cero generación de datos sintéticos.
"""

import os
import re
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional

from src.ingestion.normalizer import canonicalize_team_name

try:
    from PIL import Image, ImageEnhance, ImageFilter
except ImportError:
    Image, ImageEnhance, ImageFilter = None, None, None

try:
    import pytesseract
except ImportError:
    pytesseract = None


def configurar_tesseract():
    """
    Detecta automáticamente tesseract.exe en rutas estándar de Windows o variables de entorno.
    """
    if pytesseract is None:
        return None

    rutas_candidatas = [
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
        os.environ.get("TESSERACT_PATH", "")
    ]
    for ruta in rutas_candidatas:
        if ruta and os.path.exists(ruta):
            pytesseract.pytesseract.tesseract_cmd = ruta
            return pytesseract
    return pytesseract


def preprocesar_imagen(ruta_imagen: Path) -> Optional[Any]:
    """
    Mejora la resolución, contraste y legibilidad para captura de momios en modo oscuro/claro.
    """
    if Image is None or not ruta_imagen.exists():
        return None

    img = Image.open(ruta_imagen)
    w, h = img.size
    img_scaled = img.resize((w * 2, h * 2), Image.Resampling.LANCZOS).convert("L")
    enhancer = ImageEnhance.Contrast(img_scaled)
    img_enhanced = enhancer.enhance(2.0)
    return img_enhanced


def limpiar_nombre_equipo(texto: str) -> str:
    """
    Elimina caracteres espurios de OCR manteniendo nombres limpios de equipos.
    """
    texto = re.sub(r"^[^\wÁÉÍÓÚáéíóúÑñ]+", "", texto)
    texto = re.sub(r"[^\wÁÉÍÓÚáéíóúÑñ\s\.]+$", "", texto)
    texto = re.sub(r"\b(vs|contra|\-)\b", "", texto, flags=re.IGNORECASE)
    texto = re.sub(r"\s+", " ", texto).strip()
    return texto


def limpiar_nombre_torneo(texto_raw: str) -> str:
    """
    Normaliza el nombre del torneo detectado por OCR eliminando ruido y artefactos visuales.
    """
    limpio = re.sub(r"^(Y\s+|V\s+|▼\s+)", "", texto_raw.strip(), flags=re.I)
    limpio = re.sub(r"\s+PAGO\s+ANTICIPADO.*$", "", limpio, flags=re.I)
    limpio = limpio.strip()
    if not limpio:
        return "Liga MX - Apertura 2026"
    if "LEAGUES CUP" in limpio.upper():
        return "Leagues Cup 2026"
    if "LIGA MX" in limpio.upper():
        return "Liga MX - Apertura 2026"
    if "PREMIER" in limpio.upper():
        return "Premier League 2026"
    if "CHAMPIONS" in limpio.upper():
        return "UEFA Champions League"
    if "LALIGA" in limpio.upper() or "LA LIGA" in limpio.upper():
        return "LaLiga EA Sports"
    return limpio.title()


def extraer_cuotas_linea(line_clean: str) -> List[float]:
    """
    Extrae cuotas decimales o normaliza números enteros de 3 dígitos sin punto (ej. 165 -> 1.65).
    """
    odds = [float(x) for x in re.findall(r"\b\d+\.\d{2}\b", line_clean)]
    if len(odds) < 3:
        tokens = re.findall(r"\b\d+(?:\.\d{1,2})?\b", line_clean)
        cand_odds = []
        for t in tokens:
            val = float(t)
            if 1.05 <= val <= 35.0:
                cand_odds.append(val)
            elif 100 <= val <= 3500 and len(t) == 3:
                cand_odds.append(val / 100.0)
        if len(cand_odds) >= 3:
            odds = cand_odds[:3]
    return odds


def extraer_partidos_desde_imagen(ruta_imagen: Path) -> List[Dict[str, Any]]:
    """
    Extrae equipos y momios 1X2 desde la captura de Caliente.mx.
    Retorna lista de partidos normalizados lista para el Triaje Determinista.
    Cero fabricación de equipos sintéticos ante fallos de reconocimiento.
    """
    pyt = configurar_tesseract()
    if pyt is None:
        print("⚠️ pytesseract no está instalado o no disponible en PATH.")
        return []

    img_procesada = preprocesar_imagen(ruta_imagen)
    if img_procesada is None:
        print(f"❌ No se pudo procesar la imagen: {ruta_imagen}")
        return []

    try:
        texto_raw = pyt.image_to_string(img_procesada, config="--psm 6")
    except Exception as e:
        print(f"⚠️ Error ejecutando Tesseract OCR: {e}")
        return []

    partidos = []
    pa_global = "pago anticipado" in texto_raw.lower() or "pa" in texto_raw.lower()
    lines = texto_raw.splitlines()

    # Detección de torneo en la cabecera superior
    liga_torneo = None
    for idx, line in enumerate(lines[:25], 1):
        line_clean = line.strip()
        if not line_clean:
            continue
        norm = re.sub(r"\s+", " ", line_clean).upper()
        if any(token in norm for token in ["LEAGUES CUP", "LIGA MX", "LIGA MEXICANA", "APERTURA", "CLAUSURA", "COPA", "PREMIER", "CHAMPIONS"]):
            liga_torneo = limpiar_nombre_torneo(line_clean)
            break

    for idx, line in enumerate(lines, 1):
        line_clean = line.strip()
        if not line_clean or len(line_clean) < 10:
            continue

        odds_matches = extraer_cuotas_linea(line_clean)
        if len(odds_matches) >= 3:
            l_odd = odds_matches[0]
            e_odd = odds_matches[1]
            v_odd = odds_matches[2]
            pa = pa_global or bool(re.search(r"\b(pa|pago\s*anticipado)\b", line_clean, re.IGNORECASE))

            parts = re.split(r"empate", line_clean, flags=re.IGNORECASE)
            local = ""
            vis = ""
            if len(parts) >= 2:
                left_part = parts[0]
                right_part = parts[1]

                loc_pattern = r"([A-Za-zÁÉÍÓÚáéíóúÑñ\s\.\-]+?)\s*(?:" + re.escape(f"{l_odd:.2f}") + r"|" + re.escape(f"{int(l_odd*100)}") + r")"
                loc_match = re.search(loc_pattern, left_part)
                if loc_match:
                    local = limpiar_nombre_equipo(loc_match.group(1))
                else:
                    local = limpiar_nombre_equipo(re.sub(r"[\d\.\>\|\(\)\<\?\$\_\-]+", " ", left_part))

                vis_pattern = r"([A-Za-zÁÉÍÓÚáéíóúÑñ\s\.\-]+?)\s*(?:" + re.escape(f"{v_odd:.2f}") + r"|" + re.escape(f"{int(v_odd*100)}") + r")"
                vis_match = re.search(vis_pattern, right_part)
                if vis_match:
                    vis = limpiar_nombre_equipo(vis_match.group(1))
                else:
                    vis_cand = re.sub(re.escape(f"{e_odd:.2f}"), "", right_part)
                    vis = limpiar_nombre_equipo(re.sub(r"[\d\.\>\|\(\)\<\?\$\_\-]+", " ", vis_cand))

            local = canonicalize_team_name(local)
            vis = canonicalize_team_name(vis)

            # [GOVERNANCE-01] Descartar fila si no se extrajeron nombres de clubes válidos
            if not local or not vis or local.lower() == vis.lower():
                continue

            partido_id = f"OCR-{len(partidos)+1:02d}"
            partido = {
                "id_partido": partido_id,
                "local": local,
                "visitante": vis,
                "momios": {"L": l_odd, "E": e_odd, "V": v_odd},
                "pago_anticipado": pa,
                "liga_torneo": liga_torneo or "Liga MX - Apertura 2026",
                "identidad_partido": {
                    "id_partido": partido_id,
                    "local": local,
                    "visitante": vis,
                    "liga_torneo": liga_torneo or "Liga MX - Apertura 2026"
                }
            }
            partidos.append(partido)

    return partidos