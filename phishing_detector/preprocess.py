import re
import socket
import struct
import urllib.parse
from typing import Optional


# ── Normalización de URLs ─────────────────────────────────────────────────────

def _expand_ip_literal(host: str) -> str:
    """
    Convierte representaciones no estándar de IP a notación decimal punteada.
    Soporta: hexadecimal (0x7f000001), octal por octeto (0177.0.0.01),
    decimal largo (2130706433) y combinaciones mixtas.
    """
    # Formato hexadecimal puro: 0x7f000001
    if re.fullmatch(r'0x[0-9a-fA-F]+', host, re.IGNORECASE):
        try:
            packed = struct.pack('>I', int(host, 16))
            return socket.inet_ntoa(packed)
        except Exception:
            return host

    # Formato con puntos (puede ser octal/decimal por octeto o decimal largo)
    parts = host.split('.')
    if all(re.fullmatch(r'0?[0-9]+', p) for p in parts):
        try:
            int_parts = [
                int(p, 8) if p.startswith('0') and len(p) > 1 else int(p)
                for p in parts
            ]
            # Si hay un solo número, es decimal largo (ej. 2130706433)
            if len(int_parts) == 1:
                packed = struct.pack('>I', int_parts[0])
                return socket.inet_ntoa(packed)
            # Formato normal de 4 octetos
            if len(int_parts) == 4 and all(0 <= v <= 255 for v in int_parts):
                return '.'.join(str(v) for v in int_parts)
        except Exception:
            return host

    return host


def normalize_url(url: str) -> str:
    """
    Normaliza una URL antes del análisis:
    - Decodifica %XX (percent-encoding)
    - Expande IP literals no estándar (hex, octal, decimal largo)
    - Detecta y preserva dominios punycode (xn--)
    - Elimina el fragmento (#...) irrelevante para clasificación
    - Convierte esquema y host a minúsculas

    Args:
        url: URL cruda (puede estar codificada o mal formada)

    Returns:
        URL normalizada como string
    """
    # 1. Decodificar %XX
    url = urllib.parse.unquote(url.strip())

    try:
        parsed = urllib.parse.urlparse(url)
        host: str = parsed.hostname or ""

        # 2. Expandir representaciones no estándar de IP
        host_norm = _expand_ip_literal(host)

        # 3. Detectar punycode — se preserva, solo se anota implícitamente
        #    (los modelos aprenden que "xn--" es señal de evasión)
        port_part = f":{parsed.port}" if parsed.port else ""
        netloc_norm = f"{host_norm.lower()}{port_part}"

        # 4. Reconstruir sin fragmento
        normalized = urllib.parse.urlunparse((
            parsed.scheme.lower(),
            netloc_norm,
            parsed.path,
            parsed.params,
            parsed.query,
            "",          # fragmento descartado
        ))
    except Exception:
        # Si la URL está muy mal formada, devolver en minúsculas
        normalized = url.lower()

    return normalized


# ── Limpieza de texto ─────────────────────────────────────────────────────────

def clean_text(text: str, lowercase: bool = True) -> str:
    """
    Limpia texto crudo eliminando marcado HTML y normalizando espacios.

    Args:
        text:      Texto a limpiar (puede contener HTML)
        lowercase: Si True (por defecto), convierte a minúsculas

    Returns:
        Texto limpio
    """
    # Remover tags HTML con atributos
    text = re.sub(r'<[^>]+>', ' ', text)
    # Remover entidades HTML nombradas (&amp; &nbsp; &lt; …)
    text = re.sub(r'&[a-zA-Z]{2,8};', ' ', text)
    # Remover entidades HTML numéricas (&#160; &#x00A0; …)
    text = re.sub(r'&#x?[0-9a-fA-F]+;', ' ', text)
    # Normalizar espacios (tabs, newlines, múltiples espacios)
    text = re.sub(r'\s+', ' ', text).strip()

    if lowercase:
        text = text.lower()

    return text


# ── Preparación del input final ───────────────────────────────────────────────

def prepare_input(
    url: Optional[str] = None,
    body: Optional[str] = None,
    max_body_chars: int = 2000,
) -> str:
    """
    Combina URL y cuerpo del mensaje en el formato que consume el tokenizador.
    Formato resultante: "[URL] {url_normalizada} [BODY] {texto_limpio}"

    Tokens especiales [URL] y [BODY] funcionan como separadores semánticos
    que el modelo aprende a distinguir durante el fine-tuning.

    Args:
        url:           URL a analizar (opcional si solo hay texto)
        body:          Cuerpo del email o texto adicional (opcional)
        max_body_chars: Límite de caracteres del cuerpo antes de tokenizar;
                        evita que textos muy largos dominen el input de 512 tokens

    Returns:
        String listo para pasar al RobertaTokenizer
    """
    parts: list[str] = []

    if url:
        parts.append(f"[URL] {normalize_url(url)}")

    if body:
        cleaned = clean_text(body)[:max_body_chars]
        parts.append(f"[BODY] {cleaned}")

    return " ".join(parts)
