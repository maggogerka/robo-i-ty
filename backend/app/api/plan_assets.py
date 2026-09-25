from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import func
from sqlmodel import Session, select

from ..config import Settings, get_settings
from ..db import get_session
from ..models import AuditEvent, ObjectPlan, PlanAsset, PlanRevision, Project, User
from ..plan_assets import (
    AssetValidationError,
    detect_media_type,
    safe_original_name,
    validate_declared_type,
    validate_svg,
)
from ..recognition import RecognitionUnavailable, get_provider, provider_statuses
from ..security import InMemoryRateLimiter, get_current_user

router = APIRouter(prefix="/projects", tags=["????? ????????"])
upload_limiter = InMemoryRateLimiter(limit=12, window_seconds=60)
recognition_limiter = InMemoryRateLimiter(limit=12, window_seconds=60)


def _project(project_id: str, user: User, session: Session) -> Project:
    project = session.get(Project, project_id)
    if project is None or (project.owner_id != user.id and user.role != "admin"):
        raise HTTPException(status_code=404, detail="?????? ?? ??????")
    return project


def _asset(asset_id: str, project_id: str, session: Session) -> PlanAsset:
    asset = session.get(PlanAsset, asset_id)
    if asset is None or asset.project_id != project_id:
        raise HTTPException(status_code=404, detail="???? ????? ?? ??????")
    return asset


def _storage_path(asset: PlanAsset, settings: Settings) -> Path:
    root = settings.plan_storage_dir.resolve()
    target = (root / asset.storage_path).resolve()
    if root not in target.parents:
        raise HTTPException(status_code=500, detail="???????????? ???? ?????")
    return target


def _asset_payload(asset: PlanAsset) -> dict:
    return {
        "id": asset.id,
        "project_id": asset.project_id,
        "original_name": asset.original_name,
        "media_type": asset.media_type,
        "byte_size": asset.byte_size,
        "sha256": asset.sha256,
        "created_at": asset.created_at,
        "content_url": f"/projects/{asset.project_id}/plan-assets/{asset.id}/content",
    }


@router.get("/{project_id}/plan-assets")
def list_assets(
    project_id: str,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    _project(project_id, user, session)
    assets = session.exec(
        select(PlanAsset)
        .where(PlanAsset.project_id == project_id)
        .order_by(PlanAsset.created_at.desc())
    )
    return [_asset_payload(asset) for asset in assets]


@router.post("/{project_id}/plan-assets", status_code=201)
def upload_asset(
    project_id: str,
    request: Request,
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
    settings: Settings = Depends(get_settings),
):
    upload_limiter.check(request)
    _project(project_id, user, session)
    root = settings.plan_storage_dir.resolve()
    project_dir = (root / project_id).resolve()
    if root not in project_dir.parents:
        raise HTTPException(status_code=500, detail="???????????? ??????? ???????")
    project_dir.mkdir(parents=True, exist_ok=True)
    asset_id = str(uuid4())
    temp_path = project_dir / f"{asset_id}.part"
    digest = hashlib.sha256()
    byte_size = 0
    header = bytearray()
    try:
        with temp_path.open("xb") as target:
            while chunk := file.file.read(1024 * 1024):
                byte_size += len(chunk)
                if byte_size > settings.max_plan_asset_bytes:
                    raise HTTPException(
                        status_code=413,
                        detail=f"???? ????????? ????? {settings.max_plan_asset_bytes} ????",
                    )
                if len(header) < 4096:
                    header.extend(chunk[: 4096 - len(header)])
                digest.update(chunk)
                target.write(chunk)
        if byte_size == 0:
            raise HTTPException(status_code=422, detail="?????? ????")
        try:
            media_type, suffix = validate_declared_type(
                detect_media_type(bytes(header)),
                file.content_type,
            )
            if media_type == "image/svg+xml":
                validate_svg(temp_path.read_bytes())
        except AssetValidationError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        final_name = f"{asset_id}{suffix}"
        final_path = project_dir / final_name
        temp_path.replace(final_path)
        asset = PlanAsset(
            id=asset_id,
            project_id=project_id,
            original_name=safe_original_name(file.filename),
            media_type=media_type,
            byte_size=byte_size,
            sha256=digest.hexdigest(),
            storage_path=str(Path(project_id) / final_name),
            uploaded_by=user.id,
        )
        session.add(asset)
        object_plan = session.get(ObjectPlan, project_id)
        if object_plan is None:
            object_plan = ObjectPlan(project_id=project_id, asset_id=asset.id)
        else:
            object_plan.asset_id = asset.id
            object_plan.scale_m_per_px = None
            object_plan.scale_status = "unknown"
            object_plan.review_status = "draft"
            object_plan.updated_at = datetime.now(UTC)
        session.add(object_plan)
        session.add(
            AuditEvent(
                actor_id=user.id,
                action="project.plan_asset.upload",
                entity_type="PlanAsset",
                entity_id=asset.id,
                details={
                    "media_type": media_type,
                    "byte_size": byte_size,
                    "sha256": asset.sha256,
                },
            )
        )
        session.commit()
        session.refresh(asset)
    except Exception:
        temp_path.unlink(missing_ok=True)
        raise
    return _asset_payload(asset)


@router.get("/{project_id}/plan-assets/{asset_id}/content")
def asset_content(
    project_id: str,
    asset_id: str,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
    settings: Settings = Depends(get_settings),
):
    _project(project_id, user, session)
    asset = _asset(asset_id, project_id, session)
    path = _storage_path(asset, settings)
    if not path.is_file():
        raise HTTPException(status_code=404, detail="???? ????? ??????????? ? ?????????")
    disposition = "inline" if asset.media_type.startswith("image/") else "attachment"
    return FileResponse(
        path,
        media_type=asset.media_type,
        filename=asset.original_name,
        content_disposition_type=disposition,
        headers={
            "Cache-Control": "private, no-store",
            "X-Content-Type-Options": "nosniff",
            "Content-Security-Policy": "sandbox; default-src 'none'; style-src 'unsafe-inline'",
        },
    )


@router.get("/{project_id}/plan-recognition/providers")
def recognition_providers(
    project_id: str,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
    settings: Settings = Depends(get_settings),
):
    _project(project_id, user, session)
    return provider_statuses(settings)


@router.post("/{project_id}/plan-assets/{asset_id}/recognize")
def recognize_asset(
    project_id: str,
    asset_id: str,
    request: Request,
    provider: str = Query(default="demo", max_length=64),
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
    settings: Settings = Depends(get_settings),
):
    recognition_limiter.check(request)
    _project(project_id, user, session)
    asset = _asset(asset_id, project_id, session)
    source_path = _storage_path(asset, settings)
    if not source_path.is_file():
        raise HTTPException(status_code=404, detail="???? ????? ??????????? ? ?????????")
    try:
        selected = get_provider(provider, settings)
        result = selected.recognize(asset, source_path)
    except RecognitionUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    max_revision = session.exec(
        select(func.max(PlanRevision.revision_number)).where(PlanRevision.project_id == project_id)
    ).one()
    revision_number = int(max_revision or 0) + 1
    revision = PlanRevision(
        project_id=project_id,
        asset_id=asset.id,
        revision_number=revision_number,
        plan_data=result["plan"],
        source="model" if selected.uses_model else "demo",
        review_status="draft",
        provider_key=selected.key,
        created_by=user.id,
    )
    session.add(revision)
    session.flush()
    object_plan = session.get(ObjectPlan, project_id)
    if object_plan is None:
        object_plan = ObjectPlan(project_id=project_id)
    object_plan.asset_id = asset.id
    object_plan.current_revision_id = revision.id
    object_plan.scale_m_per_px = result["plan"].get("scale_m_per_px")
    object_plan.scale_status = result["plan"].get("scale_status", "unknown")
    object_plan.review_status = "draft"
    object_plan.provider_key = selected.key
    object_plan.updated_at = datetime.now(UTC)
    session.add(object_plan)
    session.add(
        AuditEvent(
            actor_id=user.id,
            action="project.plan.recognize",
            entity_type="PlanRevision",
            entity_id=revision.id,
            details={"provider": selected.key, "asset_id": asset.id},
        )
    )
    session.commit()
    result["revision"] = {
        "id": revision.id,
        "number": revision.revision_number,
        "review_status": revision.review_status,
    }
    return result


@router.get("/{project_id}/plan-revisions")
def list_revisions(
    project_id: str,
    limit: int = Query(default=20, ge=1, le=100),
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    _project(project_id, user, session)
    revisions = session.exec(
        select(PlanRevision)
        .where(PlanRevision.project_id == project_id)
        .order_by(PlanRevision.revision_number.desc())
        .limit(limit)
    )
    return [
        {
            "id": revision.id,
            "revision_number": revision.revision_number,
            "asset_id": revision.asset_id,
            "source": revision.source,
            "review_status": revision.review_status,
            "provider_key": revision.provider_key,
            "created_at": revision.created_at,
            "plan": revision.plan_data,
        }
        for revision in revisions
    ]
