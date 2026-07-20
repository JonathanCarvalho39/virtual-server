from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, Request, Response
from fastapi.responses import JSONResponse

import state
from models.scenario import Scenario
from services.matcher import select_scenario, resolve_response

SKIP_PREFIXES = ("admin/", "static/")


def create_dynamic_router() -> APIRouter:
    router = APIRouter()

    @router.api_route(
        "/{path:path}",
        methods=["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"],
    )
    async def catch_all(request: Request, path: str = ""):
        if any(path.startswith(p) for p in SKIP_PREFIXES):
            return JSONResponse(status_code=404, content={"error": "Not found"})

        if not state.server_running:
            return JSONResponse(
                status_code=503,
                content={"error": "Mock Server parado", "status": "stopped"},
            )

        route_path = "/" + path if path else "/"
        method = request.method.upper()

        key = (route_path, method)
        scenarios = state.routes_cache.get(key, [])

        if not scenarios:
            state.request_logs.append({
                "method": method,
                "path": route_path,
                "status": 404,
                "detail": "Rota não configurada",
            })
            return JSONResponse(
                status_code=404,
                content={"error": "Rota não configurada", "route": route_path, "method": method},
            )

        headers = dict(request.headers)
        query = dict(request.query_params)

        body: Any = None
        content_type = request.headers.get("content-type", "")
        if "json" in content_type:
            try:
                body = await request.json()
            except Exception:
                body = None
        elif "application/x-www-form-urlencoded" in content_type:
            form = await request.form()
            body = dict(form)

        scenario = select_scenario(scenarios, headers, query, body)

        if scenario is None:
            state.request_logs.append({
                "method": method,
                "path": route_path,
                "status": 422,
                "detail": "Nenhum cenário corresponde",
            })
            return JSONResponse(
                status_code=422,
                content={"error": "Nenhum cenário corresponde à requisição"},
            )

        resolved = resolve_response(scenario, headers, query, body)

        state.request_logs.append({
            "method": method,
            "path": route_path,
            "status": resolved["status"],
            "detail": scenario.name,
        })

        return Response(
            status_code=resolved["status"],
            content=json.dumps(resolved["body"], ensure_ascii=False, default=str),
            media_type="application/json",
            headers=resolved["headers"],
        )

    return router
