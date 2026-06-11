from fastapi import FastAPI

from server.db import Base, engine
from server.routes.ingest import router as ingest_router
from server.routes.live import router as live_router
from server.routes.locations import router as location_router
from server.routes.summary import legacy_router as legacy_summary_router
from server.routes.summary import summary_router


app = FastAPI(title="SIA V2 API")


@app.on_event("startup")
def on_startup() -> None:
    Base.metadata.create_all(bind=engine)


@app.get("/")
def root() -> dict[str, str]:
    return {"status": "ok", "service": "sia-v2-api"}


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(ingest_router)
app.include_router(summary_router)
app.include_router(legacy_summary_router)
app.include_router(live_router)
app.include_router(location_router)
