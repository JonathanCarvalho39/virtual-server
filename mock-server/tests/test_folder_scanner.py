from pathlib import Path

from services.folder_scanner import FolderScanner

API_DIR = Path(__file__).parent.parent / "api"


def test_scan_finds_methods():
    scanner = FolderScanner(API_DIR)
    routes = scanner.get_all_routes()
    methods = {m for _, m, _ in routes}
    assert "GET" in methods
    assert "POST" in methods
    assert "DELETE" in methods


def test_scan_route_paths():
    scanner = FolderScanner(API_DIR)
    routes = scanner.get_all_routes()
    paths = {p for p, _, _ in routes}
    assert "/v1/usuarios" in paths


def test_build_route_path():
    scanner = FolderScanner(API_DIR)
    method_dir = API_DIR / "v1" / "usuarios" / "get"
    path = scanner._build_route_path(method_dir)
    assert path == "/v1/usuarios"
