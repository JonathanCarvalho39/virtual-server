from __future__ import annotations

import json
import os
from typing import Any

from fastapi import APIRouter, Request, Response
from fastapi.responses import JSONResponse

import state
from models.scenario import Scenario
from services.matcher import select_scenario, select_scenario_with_matching_info, resolve_response

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
                "request": {
                    "headers": dict(request.headers),
                    "query": dict(request.query_params),
                },
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

        matching_info = select_scenario_with_matching_info(scenarios, headers, query, body)
        scenario = matching_info["scenario"]

        if scenario is None:
            state.request_logs.append({
                "method": method,
                "path": route_path,
                "status": 422,
                "detail": "Nenhum cenário corresponde",
                "total_scenarios": matching_info["total_scenarios"],
                "matching_candidates": matching_info["matching_candidates"],
                "request": {"headers": headers, "query": query, "body": body},
                "response": {"status": 422, "headers": {}, "body": {"error": "Nenhum cenário corresponde à requisição"}},
            })
            return JSONResponse(
                status_code=422,
                content={"error": "Nenhum cenário corresponde à requisição"},
            )

        resolved = resolve_response(scenario, headers, query, body)

        # Extract only filename (e.g., "status_totp_required_email.json")
        scenario_file = os.path.basename(scenario.file_path) if scenario.file_path else scenario.name

        state.request_logs.append({
            "method": method,
            "path": route_path,
            "status": resolved["status"],
            "detail": scenario_file,
            "total_scenarios": matching_info["total_scenarios"],
            "matching_candidates": matching_info["matching_candidates"],
            "candidate_names": matching_info["candidate_names"],
            "request": {"headers": headers, "query": query, "body": body},
            "response": {"status": resolved["status"], "headers": resolved["headers"], "body": resolved["body"]},
        })

        return Response(
            status_code=resolved["status"],
            content=json.dumps(resolved["body"], ensure_ascii=False, default=str),
            media_type="application/json",
            headers=resolved["headers"],
        )

    return router
