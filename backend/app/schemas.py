from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


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
