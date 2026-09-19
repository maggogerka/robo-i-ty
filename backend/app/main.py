from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import Session

from .api import analysis, auth, catalog, projects
from .config import get_settings
from .db import create_db_and_tables, engine
from .seed import seed_database


@asynccontextmanager
async def lifespan(_: FastAPI):
    create_db_and_tables()
    with Session(engine) as session:
        seed_database(session)
    yield


settings = get_settings()
app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="Объяснимый подбор и экономика роботизированных решений.",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(auth.router, prefix="/api/v1")
app.include_router(catalog.router, prefix="/api/v1")
app.include_router(projects.router, prefix="/api/v1")
app.include_router(analysis.router, prefix="/api/v1")


@app.get("/health", tags=["Система"])
def healthcheck():
    return {"status": "ok", "service": "robo-i-ty-api", "version": "0.1.0"}


@app.get("/api/v1/meta", tags=["Система"])
def metadata():
    return {
        "name": "Робо&Ты",
        "value_proposition": "От параметров объекта до обоснованного решения по роботизации",
        "calculation_version": "2026.09.1",
        "implemented": ["каталог", "формы объектов", "подбор", "экономика"],
        "planned": ["2D-симуляция", "PDF/CSV", "распознавание планов"],
    }
