from __future__ import annotations

import re
from pathlib import Path

from models.scenario import (
    RequestToken,
    ResponseToken,
    Scenario,
    is_regex,
    is_response_token,
    is_token,
    validate_regex,
)
from models.validation import ValidationResult
from services.folder_scanner import FolderScanner
from services.scenario_loader import ScenarioLoader


class Validator:
    VALID_METHODS = FolderScanner.VALID_METHODS

    def __init__(self, scanner: FolderScanner, loader: ScenarioLoader):
        self.scanner = scanner
        self.loader = loader

    def validate_all(self) -> ValidationResult:
        result = ValidationResult()

        if not self.scanner.api_dir.exists():
            result.add_error(str(self.scanner.api_dir), "Diretório api/ não encontrado")
            return result

        routes = self.scanner.get_all_routes()
        seen_routes: dict[tuple[str, str], str] = {}

        for route_path, method, scenarios_dir in routes:
            key = (route_path, method)
            if key in seen_routes:
                result.add_error(
                    str(scenarios_dir),
                    f"Rota duplicada: {method} {route_path} (já definida em {seen_routes[key]})",
                )
                continue
            seen_routes[key] = str(scenarios_dir)

            if method not in self.VALID_METHODS:
                result.add_error(
                    str(scenarios_dir),
                    f"Método HTTP inválido: {method}",
                )

            self._validate_scenarios(scenarios_dir, result)

        return result

    def _validate_scenarios(self, scenarios_dir: Path, result: ValidationResult):
        for json_file in scenarios_dir.glob("*.json"):
            self._validate_file(json_file, result)

    def _validate_file(self, file_path: Path, result: ValidationResult):
        try:
            raw_content = file_path.read_text(encoding="utf-8")
        except OSError as e:
            result.add_error(str(file_path), f"Erro ao ler arquivo: {e}")
            return

        try:
            import json
            raw = json.loads(raw_content)
        except Exception:
            result.add_error(str(file_path), "JSON inválido")
            return

        if not isinstance(raw, dict):
            result.add_error(str(file_path), "JSON deve ser um objeto")
            return

        self._validate_request(raw.get("request", {}), file_path, result)
        self._validate_response(raw.get("response", {}), file_path, result)

    def _validate_request(self, request: dict, file_path: Path, result: ValidationResult):
        if not isinstance(request, dict):
            return

        for section in ("headers", "query", "body"):
            rules = request.get(section, {})
            if not isinstance(rules, dict):
                continue
            for key, pattern in rules.items():
                self._validate_request_pattern(pattern, file_path, result)

    def _validate_request_pattern(self, pattern: Any, file_path: Path, result: ValidationResult):
        if not isinstance(pattern, str):
            return

        if is_regex(pattern):
            if not validate_regex(pattern):
                result.add_error(str(file_path), f"Regex inválida: {pattern}")
            return

        if is_token(pattern):
            return

    def _validate_response(self, response: dict, file_path: Path, result: ValidationResult):
        if not isinstance(response, dict):
            return

        status = response.get("status")
        if status is not None and (not isinstance(status, int) or status < 100 or status > 599):
            result.add_error(str(file_path), f"Status HTTP inválido: {status}")

        headers = response.get("headers", {})
        if isinstance(headers, dict):
            for key, value in headers.items():
                if not isinstance(value, str):
                    result.add_warning(str(file_path), f"Header value deve ser string: {key}")

        body = response.get("body")
        if body is not None:
            self._validate_response_body(body, file_path, result)

    def _validate_response_body(self, body: Any, file_path: Path, result: ValidationResult):
        if isinstance(body, str):
            if is_response_token(body):
                return
            placeholder_match = re.match(r"\{\{request\.(\w+)\.(\w+)\}\}", body)
            if placeholder_match:
                return
            return

        if isinstance(body, dict):
            for key, value in body.items():
                self._validate_response_body(value, file_path, result)
        elif isinstance(body, list):
            for item in body:
                self._validate_response_body(item, file_path, result)
