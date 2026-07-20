from __future__ import annotations

from pathlib import Path
from typing import Iterator


class FolderScanner:
    VALID_METHODS = {"GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"}

    def __init__(self, api_dir: Path):
        self.api_dir = api_dir

    def scan(self) -> Iterator[tuple[str, str, Path]]:
        if not self.api_dir.exists():
            return

        for method_dir in self._find_method_dirs():
            route_path = self._build_route_path(method_dir)
            method = method_dir.name.upper()
            yield route_path, method, method_dir

    def _find_method_dirs(self) -> Iterator[Path]:
        for json_file in self.api_dir.rglob("*.json"):
            method_dir = json_file.parent
            if method_dir.name.lower() in {m.lower() for m in self.VALID_METHODS}:
                yield method_dir

    def _build_route_path(self, method_dir: Path) -> str:
        rel = method_dir.relative_to(self.api_dir)
        parts = list(rel.parent.parts)
        route = "/" + "/".join(parts) if parts else "/"
        return route.rstrip("/") or "/"

    def get_all_routes(self) -> list[tuple[str, str, Path]]:
        seen: set[tuple[str, str]] = set()
        routes: list[tuple[str, str, Path]] = []

        for route_path, method, scenarios_dir in self.scan():
            key = (route_path, method)
            if key not in seen:
                seen.add(key)
                routes.append((route_path, method, scenarios_dir))

        return routes
