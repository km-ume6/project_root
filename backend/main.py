from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse

from backend.routers import (
    locations, departments, processes, equipments,
    inspection_items, inspection_records, inspection_results
)

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"

app = FastAPI()

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    detail = exc.detail
    if isinstance(detail, (dict, list)):
        payload = detail
    else:
        payload = {"detail": str(detail)}
    return JSONResponse(status_code=exc.status_code, content=payload)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    return JSONResponse(status_code=500, content={"detail": f"サーバーエラー: {exc}"})


# API ルーター（静的ファイルより先に登録）
app.include_router(locations.router)
app.include_router(departments.router)
app.include_router(processes.router)
app.include_router(equipments.router)
app.include_router(inspection_items.router)
app.include_router(inspection_records.router)
app.include_router(inspection_results.router)


@app.get("/")
def root():
    return RedirectResponse(url="/pages/locations.html")


@app.get("/pages")
@app.get("/pages/")
@app.get("/pages/locations")
def redirect_to_locations():
    return RedirectResponse(url="/pages/locations.html")


app.mount("/css", StaticFiles(directory=FRONTEND_DIR / "css"), name="css")
app.mount("/js", StaticFiles(directory=FRONTEND_DIR / "js"), name="js")
app.mount("/assets", StaticFiles(directory=FRONTEND_DIR / "assets"), name="assets")
app.mount("/pages", StaticFiles(directory=FRONTEND_DIR / "pages", html=True), name="pages")
