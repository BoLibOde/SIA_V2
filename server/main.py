from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from server.db import Base, engine
from server.routes.health import router as health_router
from server.routes.ingest import router as ingest_router
from server.routes.summary import router as summary_router


app = FastAPI(title="SIA V2 API", version="2.0.0")

# Allow all origins for prototype/Tailscale use – tighten in production
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup() -> None:
    Base.metadata.create_all(bind=engine)


@app.get("/")
def root() -> dict[str, str]:
    return {"status": "ok", "service": "sia-v2-api"}


app.include_router(health_router)
app.include_router(ingest_router)
app.include_router(summary_router)

