# -*- coding: utf-8 -*-
"""
[LN-QBE-137] Juez Inmutable de Integridad de Muestras MHTML
Régimen: [DIRGEN-STRICT]

Certifica que un volcado `.mhtml` capturado por la sonda `[LN-QBE-136]` es
legible, declara la cabecera MIME `Content-Type: multipart/related` y aporta
al menos un sub-bloque `text/html` con contenido factual no vacío.

Fail-Loud: toda anomalía se eleva como `MHTMLIntegrityError`. No hay
recuperación silenciosa ni retorno `False` ambiguo.
"""

from __future__ import annotations

import email
from email import errors as email_errors
from email import policy
from email.message import Message
from pathlib import Path

__all__ = ["MHTMLIntegrityError", "validar_integridad_mhtml"]

_CONTENT_TYPE_MULTIPART_RELATED = "multipart/related"
_CONTENT_TYPE_TEXT_HTML = "text/html"


class MHTMLIntegrityError(Exception):
    """Violación del contrato de integridad MHTML (`[LN-QBE-137]`)."""


def _contiene_sub_bloque_html(mensaje: Message) -> bool:
    """Busca un sub-bloque `text/html` con payload decodificado no vacío."""
    for parte in mensaje.walk():
        if parte.is_multipart():
            continue
        if parte.get_content_type() != _CONTENT_TYPE_TEXT_HTML:
            continue
        payload = parte.get_payload(decode=True)
        if isinstance(payload, bytes) and payload.strip():
            return True
    return False


def validar_integridad_mhtml(filepath: Path) -> bool:
    """
    Valida la integridad estructural de una muestra `.mhtml`.

    Returns:
        `True` si la muestra es un MIME `multipart/related` con sub-bloque
        `text/html` no vacío.

    Raises:
        MHTMLIntegrityError: archivo inexistente, vacío, no parseable como
        MIME, sin `multipart/related` o sin sub-bloque `text/html` con
        contenido.
    """
    ruta = Path(filepath)

    if not ruta.exists() or not ruta.is_file():
        raise MHTMLIntegrityError(
            f"[LN-QBE-137] Muestra inexistente o no es un archivo regular: {ruta}"
        )

    if ruta.stat().st_size == 0:
        raise MHTMLIntegrityError(
            f"[LN-QBE-137] Muestra vacía (0 bytes): {ruta}"
        )

    try:
        with ruta.open("rb") as flujo:
            mensaje = email.message_from_binary_file(flujo, policy=policy.default)
    except (OSError, email_errors.MessageError) as exc:
        raise MHTMLIntegrityError(
            f"[LN-QBE-137] Muestra ilegible o no parseable como MIME: {ruta}"
        ) from exc

    tipo_raiz = mensaje.get_content_type()
    if tipo_raiz != _CONTENT_TYPE_MULTIPART_RELATED:
        raise MHTMLIntegrityError(
            f"[LN-QBE-137] Content-Type raíz {tipo_raiz!r} != "
            f"{_CONTENT_TYPE_MULTIPART_RELATED!r}: {ruta}"
        )

    if not _contiene_sub_bloque_html(mensaje):
        raise MHTMLIntegrityError(
            f"[LN-QBE-137] Sin sub-bloque {_CONTENT_TYPE_TEXT_HTML!r} con "
            f"contenido (página vacía o bloqueo WAF): {ruta}"
        )

    return True
