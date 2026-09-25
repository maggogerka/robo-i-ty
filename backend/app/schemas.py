from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict[str, str]


class ParameterUpdate(BaseModel):
    values: dict[str, Any]


class ProjectCreate(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    object_type_code: str


class ProjectSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    object_type_code: str
    calculation_version: str
    is_demo: bool


class EconomicsRequest(BaseModel):
    solution_id: str | None = None
    overrides: dict[str, float] = Field(default_factory=dict)


class CatalogUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=250)
    price_rub: float | None = Field(default=None, ge=0)
    status: str | None = None
    description: str | None = None


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class PlanElementPayload(StrictModel):
    id: str = Field(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9_-]+$")
    kind: Literal[
        "wall", "door", "storage", "obstacle", "work_zone", "restricted_zone",
        "pickup", "dropoff", "charger",
    ]
    label: str = Field(min_length=1, max_length=120)
    x_m: float = Field(ge=0, le=2_000)
    y_m: float = Field(ge=0, le=2_000)
    width_m: float = Field(gt=0, le=500)
    height_m: float = Field(gt=0, le=500)
    rotation_deg: float = Field(default=0, ge=-360, le=360)

    confidence: float = Field(default=1, ge=0, le=1)
    source: Literal["model", "manual", "demo"] = "manual"
    review_status: Literal["needs_review", "reviewed", "confirmed"] = "reviewed"
    source_region: dict[str, Any] | None = None

class PlanPayload(StrictModel):
    name: str = Field(default="Основной план", min_length=1, max_length=120)
    width_m: float = Field(gt=1, le=2_000)
    height_m: float = Field(gt=1, le=2_000)
    elements: list[PlanElementPayload] = Field(min_length=2, max_length=250)

    asset_id: str | None = None
    scale_m_per_px: float | None = Field(default=None, gt=0, le=100)
    scale_status: Literal["unknown", "confirmed"] = "confirmed"
    review_status: Literal["draft", "reviewed", "confirmed"] = "draft"
    provider_key: str = Field(default="manual", min_length=1, max_length=64)
    @model_validator(mode="after")
    def validate_layout(self):
        ids = [item.id for item in self.elements]
        if len(ids) != len(set(ids)):
            raise ValueError("Идентификаторы элементов плана должны быть уникальны")
        if not any(item.kind == "pickup" for item in self.elements):
            raise ValueError("На плане нужна хотя бы одна зона забора")
        if not any(item.kind == "dropoff" for item in self.elements):
            raise ValueError("На плане нужна хотя бы одна зона доставки")
        for item in self.elements:
            if item.x_m + item.width_m > self.width_m or item.y_m + item.height_m > self.height_m:
                raise ValueError(f"Элемент «{item.label}» выходит за границы плана")
        return self


class SimulationRequest(StrictModel):
    robot_count: int | None = Field(default=None, ge=1, le=500)
    robot_speed_m_s: float = Field(default=1.2, gt=0, le=5)
    handling_time_seconds: float = Field(default=35, ge=0, le=3_600)
    availability_percent: float = Field(default=92, gt=0, le=100)
    robot_radius_m: float = Field(default=0.45, gt=0, le=5)
    safety_margin_m: float = Field(default=0.15, ge=0, le=5)
