from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

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
