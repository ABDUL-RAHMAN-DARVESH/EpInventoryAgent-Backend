from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api.routes import api_router
from app.core.config import get_settings
from app.core.exceptions import AppError

settings = get_settings()

app = FastAPI(title=settings.app_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError):
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.message})


app.include_router(api_router, prefix="/api/v1")


@app.get("/health")
async def health():
    return {"status": "ok"}


# A small standalone admin web page -- separate from the Expo mobile app
# entirely (different codebase, no navigation entry point from the app, never
# shipped in the APK). It's a static shell only: every action it takes goes
# through the same /api/v1/admin/* endpoints, which already enforce
# admin-only access server-side, so serving the shell itself needs no extra
# protection (same as any SPA).
ADMIN_UI_DIR = Path(__file__).resolve().parent / "admin_ui"
app.mount("/admin", StaticFiles(directory=ADMIN_UI_DIR, html=True), name="admin_ui")
