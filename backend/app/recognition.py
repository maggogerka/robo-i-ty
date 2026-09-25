from __future__ import annotations

import json
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import HTTPRedirectHandler, Request, build_opener
from uuid import uuid4

from .config import Settings
from .models import PlanAsset


class RecognitionUnavailable(RuntimeError):
    pass


class PlanRecognitionProvider(ABC):
    key: str
    display_name: str
    uses_model: bool

    @abstractmethod
    def recognize(self, asset: PlanAsset, source_path: Path) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def status(self) -> dict[str, Any]:
        raise NotImplementedError


def _demo_elements() -> list[dict[str, Any]]:
    raw = [
        ("pickup-1", "pickup", "???????", 3, 14, 8, 8),
        ("storage-1", "storage", "??????? A", 18, 3, 8, 13),
        ("storage-2", "storage", "??????? B", 31, 3, 8, 13),
        ("storage-3", "storage", "??????? C", 18, 21, 8, 12),
        ("storage-4", "storage", "??????? D", 31, 21, 8, 12),
        ("dropoff-1", "dropoff", "????????", 49, 14, 8, 8),
        ("charger-1", "charger", "???????", 48, 4, 7, 5),
    ]
    return [
        {
            "id": element_id,
            "kind": kind,
            "label": label,
            "x_m": x,
            "y_m": y,
            "width_m": width,
            "height_m": height,
            "rotation_deg": 0,
            "confidence": 1,
            "source": "demo",
            "review_status": "needs_review",
            "source_region": None,
        }
        for element_id, kind, label, x, y, width, height in raw
    ]


class DemoPlanRecognitionProvider(PlanRecognitionProvider):
    key = "demo"
    display_name = "???????????????? ??????"
    uses_model = False

    def recognize(self, asset: PlanAsset, source_path: Path) -> dict[str, Any]:
        return {
            "provider": {
                "key": self.key,
                "display_name": self.display_name,
                "uses_model": False,
            },
            "plan": {
                "name": f"????????: {asset.original_name}",
                "width_m": 60,
                "height_m": 36,
                "asset_id": asset.id,
                "scale_m_per_px": None,
                "scale_status": "unknown",
                "review_status": "draft",
                "provider_key": self.key,
                "elements": _demo_elements(),
            },
            "warnings": [
                "??????????? ???????????????? ??????, ? ?? ?????????.",
                "????????? ?? ????????? ?? ???????????? ?????: ????????? ??? ???????? ? ???????.",
            ],
            "unresolved": ["scale", "source_alignment"],
            "model_versions": {},
        }

    def status(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "display_name": self.display_name,
            "available": True,
            "uses_model": False,
            "formats": sorted(
                ["application/pdf", "image/png", "image/jpeg", "image/webp", "image/svg+xml"]
            ),
            "note": "?????? ???????? ??? GPU; ?????????? ??????? ?????????????? ?????.",
        }


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise RecognitionUnavailable("????????? ????????? ????????? ????????????? ??????")


class YytsiPlanRecognitionProvider(PlanRecognitionProvider):
    key = "yytsi_floorplan"
    display_name = "Yytsi Floorplan Segmentation"
    uses_model = True

    def __init__(self, base_url: str | None):
        self.base_url = base_url.rstrip("/") if base_url else None
        if self.base_url:
            parsed = urlparse(self.base_url)
            if parsed.scheme != "http" or parsed.hostname not in {"127.0.0.1", "localhost", "::1"}:
                raise RecognitionUnavailable(
                    "YYTSI_PROVIDER_URL ?????? ????????? ?????? ?? ????????? HTTP-??????"
                )
        self.opener = build_opener(_NoRedirect)

    def status(self) -> dict[str, Any]:
        available = False
        detail = "URL ?????????? inference-??????? ?? ?????"
        if self.base_url:
            try:
                response = self.opener.open(f"{self.base_url}/healthz", timeout=2)
                available = response.status == 200
                detail = "????????? ?????? ????????" if available else f"HTTP {response.status}"
            except (HTTPError, URLError, OSError, RecognitionUnavailable) as exc:
                detail = f"????????? ?????? ??????????: {type(exc).__name__}"
        return {
            "key": self.key,
            "display_name": self.display_name,
            "available": available,
            "uses_model": True,
            "formats": ["image/svg+xml"],
            "note": detail,
            "license": "MIT",
            "weights": "best.safetensors, ????? 98 ??; ?? ?????? ? ???????????",
        }

    def recognize(self, asset: PlanAsset, source_path: Path) -> dict[str, Any]:
        if not self.base_url:
            raise RecognitionUnavailable("????????? Yytsi-????????? ?? ????????")
        if asset.media_type != "image/svg+xml":
            raise RecognitionUnavailable("Yytsi-????????? ???? ?????? ????????? ?????? SVG")
        boundary = f"----robo-{uuid4().hex}"
        payload = source_path.read_bytes()
        body = (
            (
                f"--{boundary}\r\n"
                'Content-Disposition: form-data; name="svg"; filename="plan.svg"\r\n'
                "Content-Type: image/svg+xml\r\n\r\n"
            ).encode()
            + payload
            + f"\r\n--{boundary}--\r\n".encode()
        )
        request = Request(
            f"{self.base_url}/extract",
            data=body,
            method="POST",
            headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        )
        try:
            with self.opener.open(request, timeout=90) as response:
                raw = response.read(10 * 1024 * 1024 + 1)
        except (HTTPError, URLError, OSError) as exc:
            raise RecognitionUnavailable("?????? ?????????? Yytsi-?????????") from exc
        if len(raw) > 10 * 1024 * 1024:
            raise RecognitionUnavailable("????? Yytsi-?????????? ????????? ?????")
        try:
            result = json.loads(raw)
            width_px, height_px = result["canvas_size"]
            polygons = result["polygons"]
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise RecognitionUnavailable("Yytsi-????????? ?????? ??????????? JSON") from exc
        width_m = 60.0
        height_m = max(2.0, round(width_m * float(height_px) / float(width_px), 3))
        scale_x = width_m / float(width_px)
        scale_y = height_m / float(height_px)
        elements: list[dict[str, Any]] = []
        class_map = {"wall": "wall", "door": "door"}
        for source_class, target_kind in class_map.items():
            for index, polygon in enumerate(polygons.get(source_class, []), start=1):
                points = polygon.get("outer") or []
                if len(points) < 3:
                    continue
                xs = [float(point[0]) for point in points]
                ys = [float(point[1]) for point in points]
                x0, x1 = min(xs), max(xs)
                y0, y1 = min(ys), max(ys)
                elements.append(
                    {
                        "id": f"{target_kind}-{index}",
                        "kind": target_kind,
                        "label": "?????" if target_kind == "wall" else "?????",
                        "x_m": round(x0 * scale_x, 3),
                        "y_m": round(y0 * scale_y, 3),
                        "width_m": max(0.05, round((x1 - x0) * scale_x, 3)),
                        "height_m": max(0.05, round((y1 - y0) * scale_y, 3)),
                        "rotation_deg": 0,
                        "confidence": 0.65,
                        "source": "model",
                        "review_status": "needs_review",
                        "source_region": {
                            "page": 1,
                            "bbox_px": [x0, y0, x1, y1],
                            "method": "yytsi_polygon_bbox",
                        },
                    }
                )
        return {
            "provider": {
                "key": self.key,
                "display_name": self.display_name,
                "uses_model": True,
            },
            "plan": {
                "name": f"??????????: {asset.original_name}",
                "width_m": width_m,
                "height_m": height_m,
                "asset_id": asset.id,
                "scale_m_per_px": None,
                "scale_status": "unknown",
                "review_status": "draft",
                "provider_key": self.key,
                "elements": elements[:250],
            },
            "warnings": [
                "??????? ?? ???????????: ??????????? ??????? ???????? ???????? ?????????????.",
                (
                    "?????? ?????????? ?????? floor/wall/door/window; "
                    "????????????? ????? ??????????? ???????."
                ),
            ],
            "unresolved": ["scale", "pickup", "dropoff", "industrial_objects"],
            "model_versions": {"yytsi_floorplan": "external-best.safetensors"},
        }


def get_provider(key: str, settings: Settings) -> PlanRecognitionProvider:
    if key == "demo":
        return DemoPlanRecognitionProvider()
    if key == "yytsi_floorplan":
        return YytsiPlanRecognitionProvider(settings.yytsi_provider_url)
    raise RecognitionUnavailable("??????????? ????????? ?????????????")


def provider_statuses(settings: Settings) -> list[dict[str, Any]]:
    providers: list[PlanRecognitionProvider] = [DemoPlanRecognitionProvider()]
    try:
        providers.append(YytsiPlanRecognitionProvider(settings.yytsi_provider_url))
    except RecognitionUnavailable as exc:
        return [
            providers[0].status(),
            {
                "key": "yytsi_floorplan",
                "display_name": "Yytsi Floorplan Segmentation",
                "available": False,
                "uses_model": True,
                "formats": ["image/svg+xml"],
                "note": str(exc),
                "license": "MIT",
            },
        ]
    return [provider.status() for provider in providers]
