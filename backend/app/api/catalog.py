from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, col, select

from ..db import get_session
from ..models import AuditEvent, RobotSolution, User
from ..schemas import CatalogUpdate
from ..security import require_admin

router = APIRouter(prefix="/catalog", tags=["Каталог"])


@router.get("")
def get_catalog(
    search: str | None = None,
    industry: str | None = None,
    status: str | None = None,
    solution_type: str | None = None,
    limit: int = Query(default=60, ge=1, le=223),
    offset: int = Query(default=0, ge=0),
    session: Session = Depends(get_session),
):
    query = select(RobotSolution)
    if search:
        pattern = f"%{search.strip()}%"
        query = query.where(
            col(RobotSolution.name).ilike(pattern) | col(RobotSolution.manufacturer).ilike(pattern)
        )
    if industry:
        query = query.where(RobotSolution.industry == industry)
    if status:
        query = query.where(RobotSolution.status == status)
    if solution_type:
        query = query.where(RobotSolution.catalog_type == solution_type)
    all_items = list(session.exec(query.order_by(RobotSolution.name)))
    return {
        "count": len(all_items),
        "items": all_items[offset : offset + limit],
        "source": "catalog_export_v4.csv",
        "source_status": "source_present",
    }


@router.patch("/{solution_id}")
def update_solution(
    solution_id: str,
    payload: CatalogUpdate,
    admin: User = Depends(require_admin),
    session: Session = Depends(get_session),
):
    solution = session.get(RobotSolution, solution_id)
    if solution is None:
        raise HTTPException(status_code=404, detail="Решение не найдено")
    changes = payload.model_dump(exclude_unset=True)
    for key, value in changes.items():
        setattr(solution, key, value)
    session.add(
        AuditEvent(
            actor_id=admin.id,
            action="catalog.solution.update",
            entity_type="RobotSolution",
            entity_id=solution.id,
            details={"fields": sorted(changes)},
        )
    )
    session.commit()
    session.refresh(solution)
    return solution
