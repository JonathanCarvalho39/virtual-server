from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.requests import Request
from fastapi.responses import HTMLResponse

from routes import admin
from routes.dynamic import create_dynamic_router
from services import scanner, loader
from services.watcher import WatchdogService
from config import API_DIR
import state


def load_scenarios():
    state.routes_cache = {}
    for route_path, method, scenarios_dir in scanner.scan():
        scenarios = loader.load_all(scenarios_dir)
        key = (route_path, method.upper())
        state.routes_cache[key] = scenarios
        api_key = ("/api" + route_path, method.upper())
        state.routes_cache[api_key] = scenarios


watcher = WatchdogService(API_DIR, load_scenarios)


@asynccontextmanager
async def lifespan(app: FastAPI):
    load_scenarios()
    watcher.start()
    yield
    watcher.stop()


app = FastAPI(title="Mock Server", lifespan=lifespan)

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

app.include_router(admin.router, prefix="/admin")


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse(request, "index.html")


app.include_router(create_dynamic_router())
