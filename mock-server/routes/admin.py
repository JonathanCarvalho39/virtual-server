from __future__ import annotations

import json
import re
import shutil
import zipfile
import tempfile
from pathlib import Path

from fastapi import APIRouter, UploadFile, File, Form
from fastapi.responses import JSONResponse

from services import scanner, loader
from services.validator import Validator
from config import API_DIR
from config import HOST, PORT
import state

router = APIRouter()

validator = Validator(scanner, loader)

VALID_METHODS = {"get", "post", "put", "patch", "delete", "head", "options"}


def load_scenarios():
    state.routes_cache = {}
    for route_path, method, scenarios_dir in scanner.scan():
        scenarios = loader.load_all(scenarios_dir)
        key = (route_path, method.upper())
        state.routes_cache[key] = scenarios
        api_key = ("/api" + route_path, method.upper())
        state.routes_cache[api_key] = scenarios


def _reload_cache():
    state.routes_cache = {}
    for route_path, method, scenarios_dir in scanner.scan():
        scenarios = loader.load_all(scenarios_dir)
        key = (route_path, method.upper())
        state.routes_cache[key] = scenarios
        api_key = ("/api" + route_path, method.upper())
        state.routes_cache[api_key] = scenarios


def _is_within_api(path: Path) -> bool:
    try:
        path.resolve().relative_to(API_DIR.resolve())
        return True
    except ValueError:
        return False


@router.get("/status")
async def status():
    routes = scanner.get_all_routes()
    return {
        "running": state.server_running,
        "routes_count": len(routes),
        "api_dir": str(API_DIR),
        "host": HOST,
        "port": PORT,
    }


@router.get("/validate")
async def validate():
    result = validator.validate_all()
    return {
        "valid": result.is_valid,
        "errors": [
            {"file": e.file, "message": e.message, "line": e.line}
            for e in result.errors
        ],
        "warnings": [
            {"file": w.file, "message": w.message, "line": w.line}
            for w in result.warnings
        ],
    }


def _build_tree(path: Path) -> dict:
    tree = {}
    if not path.exists():
        return tree
    for item in sorted(path.iterdir()):
        if item.name.startswith('.'):
            continue
        if item.is_dir():
            tree[item.name] = _build_tree(item)
        elif item.suffix == ".json":
            tree[item.name] = None
    return tree


@router.get("/tree")
async def get_tree():
    return {"tree": _build_tree(API_DIR)}


@router.get("/routes")
async def list_routes():
    routes = scanner.get_all_routes()
    route_list = []
    seen: set[tuple[str, str]] = set()

    for route_path, method, scenarios_dir in routes:
        key = (route_path, method)
        if key in seen:
            continue
        seen.add(key)

        scenarios = loader.load_all(scenarios_dir)
        route_list.append({
            "path": route_path,
            "method": method,
            "scenarios": [
                {"name": s.name, "specificity": s.specificity, "file": s.file_path}
                for s in scenarios
            ],
        })

    return {"routes": route_list}


@router.get("/scenario")
async def get_scenario(path: str):
    if path.startswith("/api/"):
        file_path = API_DIR / path[5:]
    elif path.startswith("/api"):
        file_path = API_DIR / path[4:]
    else:
        file_path = Path(path)
    if not file_path.exists():
        return JSONResponse(status_code=404, content={"error": "Arquivo não encontrado"})
    try:
        data = json.loads(file_path.read_text(encoding="utf-8"))
        return data
    except Exception as e:
        return JSONResponse(status_code=400, content={"error": str(e)})


@router.post("/scenario")
async def save_scenario(payload: dict):
    path = payload.get("path", "")
    content = payload.get("content", "")

    if path.startswith("/api/"):
        file_path = API_DIR / path[5:]
    elif path.startswith("/api"):
        file_path = API_DIR / path[4:]
    else:
        file_path = Path(path)

    if not file_path.exists():
        return JSONResponse(status_code=404, content={"error": "Arquivo não encontrado"})

    try:
        json.loads(content)
    except json.JSONDecodeError as e:
        return JSONResponse(status_code=400, content={"error": f"JSON inválido: {e}"})

    try:
        file_path.write_text(content, encoding="utf-8")
        _reload_cache()
        return {"status": "saved", "path": str(file_path)}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@router.post("/start")
async def start_server():
    state.server_running = True
    return {"status": "running", "host": HOST, "port": PORT}


@router.post("/stop")
async def stop_server():
    state.server_running = False
    return {"status": "stopped"}


@router.get("/logs")
async def get_logs():
    return {"logs": list(state.request_logs)}


@router.post("/logs/clear")
async def clear_logs():
    state.request_logs.clear()
    return {"status": "cleared"}


def _resolve_parent(parent_path: str) -> Path:
    if not parent_path:
        return API_DIR
    rel = parent_path.lstrip("/")
    if rel.startswith("api/"):
        rel = rel[4:]
    if not rel:
        return API_DIR
    return API_DIR / rel


@router.post("/create-folder")
async def create_folder(payload: dict):
    name = payload.get("name", "").strip()
    parent_path = payload.get("parent", "")

    if not name:
        return JSONResponse(status_code=400, content={"error": "Nome é obrigatório"})

    if not re.match(r"^[a-zA-Z0-9_\-.]+$", name):
        return JSONResponse(status_code=400, content={"error": "Nome inválido. Use apenas letras, números, _, -, ."})

    parent = _resolve_parent(parent_path)
    new_dir = parent / name

    if not _is_within_api(new_dir):
        return JSONResponse(status_code=403, content={"error": "Fora do diretório api/"})

    if new_dir.exists():
        return JSONResponse(status_code=409, content={"error": "Já existe"})

    try:
        new_dir.mkdir(parents=True, exist_ok=True)
        _reload_cache()
        return {"status": "created", "path": str(new_dir)}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@router.post("/create-file")
async def create_file(payload: dict):
    name = payload.get("name", "").strip()
    parent_path = payload.get("parent", "")
    content = payload.get("content", "{}")

    if not name:
        return JSONResponse(status_code=400, content={"error": "Nome é obrigatório"})

    if not name.endswith(".json"):
        return JSONResponse(status_code=400, content={"error": "Arquivo deve terminar com .json"})

    parent = _resolve_parent(parent_path)
    new_file = parent / name

    if not _is_within_api(new_file):
        return JSONResponse(status_code=403, content={"error": "Fora do diretório api/"})

    if new_file.exists():
        return JSONResponse(status_code=409, content={"error": "Já existe"})

    try:
        json.loads(content)
    except json.JSONDecodeError as e:
        return JSONResponse(status_code=400, content={"error": f"JSON inválido: {e}"})

    try:
        new_file.write_text(content, encoding="utf-8")
        _reload_cache()
        return {"status": "created", "path": str(new_file)}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@router.post("/create-method")
async def create_method(payload: dict):
    method = payload.get("method", "").strip().lower()
    parent_path = payload.get("parent", "")

    if method not in VALID_METHODS:
        return JSONResponse(status_code=400, content={"error": f"Método inválido. Use: {', '.join(sorted(VALID_METHODS))}"})

    parent = _resolve_parent(parent_path)
    method_dir = parent / method

    if not _is_within_api(method_dir):
        return JSONResponse(status_code=403, content={"error": "Fora do diretório api/"})

    if method_dir.exists():
        return JSONResponse(status_code=409, content={"error": "Método já existe"})

    try:
        method_dir.mkdir(parents=True, exist_ok=True)
        _reload_cache()
        return {"status": "created", "path": str(method_dir)}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@router.post("/rename")
async def rename(payload: dict):
    old_path = Path(payload.get("path", ""))
    new_name = payload.get("new_name", "").strip()

    if not new_name:
        return JSONResponse(status_code=400, content={"error": "Novo nome é obrigatório"})

    if not _is_within_api(old_path):
        return JSONResponse(status_code=403, content={"error": "Fora do diretório api/"})

    if not old_path.exists():
        return JSONResponse(status_code=404, content={"error": "Não encontrado"})

    new_path = old_path.parent / new_name

    if new_path.exists():
        return JSONResponse(status_code=409, content={"error": "Já existe"})

    try:
        old_path.rename(new_path)
        _reload_cache()
        return {"status": "renamed", "path": str(new_path)}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@router.post("/delete")
async def delete_item(payload: dict):
    path_str = payload.get("path", "")

    if path_str.startswith("/api/"):
        rel = path_str[5:]
    elif path_str.startswith("/api"):
        rel = path_str[4:]
    else:
        rel = path_str.lstrip("/")

    path = API_DIR / rel if rel else API_DIR

    if not _is_within_api(path):
        return JSONResponse(status_code=403, content={"error": "Fora do diretório api/"})

    if not path.exists():
        return JSONResponse(status_code=404, content={"error": "Não encontrado"})

    try:
        if path.is_dir():
            import shutil
            shutil.rmtree(path)
        else:
            path.unlink()
        _reload_cache()
        return {"status": "deleted", "path": path_str}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


MAX_UPLOAD_SIZE = 50 * 1024 * 1024  # 50MB


@router.post("/upload")
async def upload_folder(
    file: UploadFile = File(...),
    target: str = Form(""),
):
    content = await file.read()
    await file.close()
    if len(content) > MAX_UPLOAD_SIZE:
        return JSONResponse(
            status_code=413,
            content={"error": f"Arquivo muito grande. Tamanho máximo: {MAX_UPLOAD_SIZE // (1024*1024)}MB"}
        )

    target_dir = API_DIR
    if target:
        rel = target.lstrip("/")
        if rel.startswith("api/"):
            rel = rel[4:]
        if rel:
            target_dir = API_DIR / rel

    if not _is_within_api(target_dir):
        return JSONResponse(status_code=403, content={"error": "Fora do diretório api/"})

    try:
        target_dir.mkdir(parents=True, exist_ok=True)

        if file.filename.endswith(".zip"):
            with tempfile.TemporaryDirectory() as tmp_dir:
                zip_path = Path(tmp_dir) / file.filename
                zip_path.write_bytes(content)

                with zipfile.ZipFile(zip_path, "r") as zf:
                    zf.extractall(tmp_dir)

                extracted = Path(tmp_dir)
                items = list(extracted.iterdir())
                if len(items) == 1 and items[0].is_dir():
                    src = items[0]
                else:
                    src = extracted

                for item in src.iterdir():
                    dest = target_dir / item.name
                    if dest.exists():
                        if dest.is_dir():
                            shutil.rmtree(dest)
                        else:
                            dest.unlink()
                    if item.is_dir():
                        shutil.copytree(item, dest)
                    else:
                        shutil.copy2(item, dest)
        else:
            dest = target_dir / file.filename
            if dest.exists():
                dest.unlink()
            dest.write_bytes(content)

        _reload_cache()

        routes = scanner.get_all_routes()
        total_routes = len(routes)
        total_scenarios = sum(
            len(loader.load_all(sd)) for _, _, sd in routes
        )

        return {
            "status": "uploaded",
            "target": str(target_dir),
            "filename": file.filename,
            "routes": total_routes,
            "scenarios": total_scenarios,
        }
    except zipfile.BadZipFile:
        return JSONResponse(status_code=400, content={"error": "Arquivo ZIP inválido"})
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@router.post("/upload-batch")
async def upload_batch(
    files: list[UploadFile] = File(...),
    target: str = Form(""),
):
    target_dir = API_DIR
    if target:
        rel = target.lstrip("/")
        if rel.startswith("api/"):
            rel = rel[4:]
        if rel:
            target_dir = API_DIR / rel

    if not _is_within_api(target_dir):
        return JSONResponse(status_code=403, content={"error": "Fora do diretório api/"})

    try:
        file_contents = []
        total_size = 0
        for f in files:
            content = await f.read()
            await f.close()
            total_size += len(content)
            if total_size > MAX_UPLOAD_SIZE:
                return JSONResponse(
                    status_code=413,
                    content={"error": f"Arquivos muito grandes. Tamanho máximo: {MAX_UPLOAD_SIZE // (1024*1024)}MB"}
                )
            file_contents.append((f, content))

        target_dir.mkdir(parents=True, exist_ok=True)

        for f, content in file_contents:
            rel_path = f.filename
            if rel_path.startswith("/"):
                rel_path = rel_path[1:]

            dest = target_dir / rel_path
            dest.parent.mkdir(parents=True, exist_ok=True)

            if dest.exists():
                if dest.is_dir():
                    shutil.rmtree(dest)
                else:
                    dest.unlink()

            dest.write_bytes(content)

        _reload_cache()

        routes = scanner.get_all_routes()
        total_routes = len(routes)
        total_scenarios = sum(
            len(loader.load_all(sd)) for _, _, sd in routes
        )

        return {
            "status": "uploaded",
            "target": str(target_dir),
            "files": len(files),
            "routes": total_routes,
            "scenarios": total_scenarios,
        }
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})
