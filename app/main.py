from fastapi import FastAPI, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from pathlib import Path

from app.api.v1 import api_router
from app.core.config import settings
from app.db.session import get_db

app = FastAPI(
    title="RBAC Attendance API",
    version="0.1.0",
    description="FastAPI RBAC system with PostgreSQL",
    swagger_ui_parameters={"persistAuthorization": True}
)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add security scheme for Swagger UI
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )
    openapi_schema["components"]["securitySchemes"] = {
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT"
        }
    }
    openapi_schema["security"] = [{"BearerAuth": []}]
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"

app.include_router(api_router, prefix="/api/v1")

app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")

@app.get("/health", summary="System health check")
async def health_check(db: AsyncSession = Depends(get_db)):
    try:
        await db.execute(text("SELECT 1"))
        return {
            "status": "ok",
            "database": "connected",
            "environment": settings.POSTGRES_DB,
        }
    except Exception as e:
        return {
            "status": "error",
            "database": "disconnected",
            "detail": str(e),
        }, 500

