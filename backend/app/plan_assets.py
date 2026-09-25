from __future__ import annotations

import re
from pathlib import Path
from xml.etree import ElementTree

ALLOWED_MEDIA_TYPES = {
    "application/pdf": ".pdf",
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/webp": ".webp",
    "image/svg+xml": ".svg",
}

DECLARED_ALIASES = {
    "application/pdf": {"application/pdf"},
    "image/png": {"image/png"},
    "image/jpeg": {"image/jpeg", "image/jpg"},
    "image/webp": {"image/webp"},
    "image/svg+xml": {"image/svg+xml", "text/xml", "application/xml"},
}

_SVG_BLOCKED = re.compile(
    rb"<!doctype|<!entity|<script\b|javascript\s*:|\bon[a-z]+\s*=|"
    rb"(?:href|src)\s*=\s*['\"]\s*(?:https?:|//|data:)|url\s*\(",
    re.IGNORECASE,
)


class AssetValidationError(ValueError):
    pass


def safe_original_name(filename: str | None) -> str:
    name = Path(filename or "plan").name
    name = "".join(character for character in name if character.isprintable())
    return (name.strip() or "plan")[:255]


def detect_media_type(header: bytes) -> str | None:
    if header.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if header.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if len(header) >= 12 and header[:4] == b"RIFF" and header[8:12] == b"WEBP":
        return "image/webp"
    if b"%PDF-" in header[:1024]:
        return "application/pdf"
    prefix = header[:4096].lstrip(b"\xef\xbb\xbf\x00\t\r\n ")
    if prefix.startswith(b"<?xml") or prefix.lower().startswith(b"<svg"):
        if b"<svg" in prefix.lower():
            return "image/svg+xml"
    return None


def validate_declared_type(detected: str | None, declared: str | None) -> tuple[str, str]:
    if detected not in ALLOWED_MEDIA_TYPES:
        raise AssetValidationError("?????? ????? ?? ????????? ??? ?? ??????????????")
    normalized = (declared or "").split(";", 1)[0].strip().lower()
    if normalized not in DECLARED_ALIASES[detected]:
        raise AssetValidationError(
            f"MIME ????? ?? ????????? ? ??????????: ??????? {normalized or 'unknown'}, "
            f"????????? {detected}"
        )
    return detected, ALLOWED_MEDIA_TYPES[detected]


def validate_svg(data: bytes) -> None:
    if _SVG_BLOCKED.search(data):
        raise AssetValidationError("SVG ???????? ??????????? ???????? ??? ??????? ???????")
    try:
        root = ElementTree.fromstring(data)
    except ElementTree.ParseError as exc:
        raise AssetValidationError("???????????? SVG") from exc
    if not root.tag.lower().endswith("svg"):
        raise AssetValidationError("???????? ??????? SVG ?? ??????")
    if sum(1 for _ in root.iter()) > 50_000:
        raise AssetValidationError("SVG ???????? ??????? ????? ?????????")
