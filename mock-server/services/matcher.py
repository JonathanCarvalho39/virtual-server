from __future__ import annotations

import re
import uuid
import random
import string
from datetime import datetime, timezone
from typing import Any

from models.scenario import (
    RequestToken,
    ResponseToken,
    Scenario,
    is_regex,
    is_response_token,
    is_token,
)


SKIP_HEADERS = {"content-length", "host", "connection", "transfer-encoding"}


def match_request(scenario: Scenario, headers: dict, query: dict, body: Any) -> bool:
    for key, pattern in scenario.request.headers.items():
        if key.lower() in SKIP_HEADERS:
            continue
        value = _get_header(headers, key)
        if not _match_value(pattern, value):
            return False

    for key, pattern in scenario.request.query.items():
        value = query.get(key)
        if not _match_value(pattern, value):
            return False

    # Body matching - handle both dict and list patterns
    body_pattern = scenario.request.body
    if isinstance(body_pattern, list):
        # List body pattern - match if body is a list and patterns match
        if not isinstance(body, list):
            return False
    elif isinstance(body_pattern, dict) and body_pattern:
        # Dict body pattern
        if not isinstance(body, dict):
            return False
        for key, pattern in body_pattern.items():
            value = body.get(key)
            if not _match_value(pattern, value):
                return False

    return True


def select_scenario(
    scenarios: list[Scenario],
    headers: dict,
    query: dict,
    body: Any,
) -> Scenario | None:
    candidates = [
        s for s in scenarios if match_request(s, headers, query, body)
    ]

    if not candidates:
        return None

    candidates.sort(key=lambda s: s.specificity, reverse=True)
    return candidates[0]


def select_scenario_with_matching_info(
    scenarios: list[Scenario],
    headers: dict,
    query: dict,
    body: Any,
) -> dict:
    """Seleciona cenário e retorna informações detalhadas sobre o matching."""
    candidates = [
        s for s in scenarios if match_request(s, headers, query, body)
    ]

    selected = None
    if candidates:
        candidates.sort(key=lambda s: s.specificity, reverse=True)
        selected = candidates[0]

    return {
        "scenario": selected,
        "total_scenarios": len(scenarios),
        "matching_candidates": len(candidates),
        "candidate_names": [s.name for s in candidates] if candidates else [],
        "selected_name": selected.name if selected else None,
    }


def resolve_response(scenario: Scenario, headers: dict, query: dict, body: Any) -> dict:
    resolved_headers = dict(scenario.response.headers)
    resolved_body = _resolve_tokens(scenario.response.body, headers, query, body)

    return {
        "status": scenario.response.status,
        "headers": resolved_headers,
        "body": resolved_body,
    }


def _match_value(pattern: Any, value: Any) -> bool:
    if isinstance(pattern, dict):
        if not isinstance(value, dict):
            return False
        for k, v in pattern.items():
            if not _match_value(v, value.get(k)):
                return False
        return True

    if not isinstance(pattern, str):
        return str(pattern) == str(value) if value is not None else False

    if is_token(pattern):
        return _match_token(pattern, value)

    if is_regex(pattern):
        return _match_regex(pattern, value)

    return str(pattern) == str(value) if value is not None else False


def _match_token(token: str, value: Any) -> bool:
    # $$...$$ wildcard patterns
    if token.startswith("$$") and token.endswith("$$"):
        return value is not None

    if token == RequestToken.ANY:
        return value is not None
    if token == RequestToken.MISSING:
        return value is None
    if token == RequestToken.NULL:
        return value is None
    if token == RequestToken.EMPTY:
        return value == "" or value is None
    if token == RequestToken.STRING:
        return isinstance(value, str)
    if token == RequestToken.NUMBER:
        return isinstance(value, (int, float))
    if token == RequestToken.BOOLEAN:
        return isinstance(value, bool)
    if token == RequestToken.ARRAY:
        return isinstance(value, list)
    if token == RequestToken.OBJECT:
        return isinstance(value, dict)
    if token == RequestToken.UUID:
        if value is None:
            return False
        try:
            uuid.UUID(str(value))
            return True
        except ValueError:
            return False
    if token == RequestToken.DATE:
        if value is None:
            return False
        try:
            datetime.fromisoformat(str(value).replace("Z", "+00:00"))
            return True
        except ValueError:
            return False
    return False


def _match_regex(pattern: str, value: Any) -> bool:
    if value is None:
        return False
    # Convert $$^...$$ to ^...$
    if pattern.startswith("$$^") and pattern.endswith("$$"):
        pattern = pattern[2:-2] + "$"
        if not pattern.endswith("$"):
            pattern = pattern + "$"
    try:
        return bool(re.fullmatch(pattern, str(value)))
    except re.error:
        return False


def _resolve_tokens(value: Any, headers: dict, query: dict, body: Any) -> Any:
    if isinstance(value, str):
        return _resolve_string_token(value, headers, query, body)
    if isinstance(value, dict):
        return {k: _resolve_tokens(v, headers, query, body) for k, v in value.items()}
    if isinstance(value, list):
        return [_resolve_tokens(item, headers, query, body) for item in value]
    return value


def _resolve_string_token(value: str, headers: dict, query: dict, body: Any) -> str:
    if value == ResponseToken.UUID:
        return str(uuid.uuid4())
    if value == ResponseToken.NOW:
        return datetime.now(timezone.utc).isoformat()
    if value == ResponseToken.TIMESTAMP:
        return str(int(datetime.now(timezone.utc).timestamp()))
    if value.startswith("/random/int/"):
        return _resolve_random_int(value)
    if value.startswith("/random/string/"):
        return _resolve_random_string(value)
    if value == ResponseToken.RANDOM_BOOLEAN:
        return str(random.choice([True, False])).lower()

    placeholder_match = re.match(r"\{\{request\.(\w+)\.(\w+)\}\}", value)
    if placeholder_match:
        source = placeholder_match.group(1)
        field = placeholder_match.group(2)
        return _resolve_placeholder(source, field, headers, query, body)

    return value


def _resolve_random_int(token: str) -> str:
    parts = token.rstrip("/").split("/")
    if len(parts) >= 5:
        lo, hi = int(parts[3]), int(parts[4])
        return str(random.randint(lo, hi))
    return str(random.randint(0, 100))


def _resolve_random_string(token: str) -> str:
    parts = token.rstrip("/").split("/")
    length = int(parts[3]) if len(parts) >= 4 else 10
    chars = string.ascii_letters + string.digits
    return "".join(random.choices(chars, k=length))


def _resolve_placeholder(source: str, field: str, headers: dict, query: dict, body: Any) -> str:
    if source == "body" and isinstance(body, dict):
        return str(body.get(field, ""))
    if source == "query":
        return str(query.get(field, ""))
    if source == "header":
        return _get_header(headers, field)
    return ""


def _get_header(headers: dict, key: str) -> str | None:
    for k, v in headers.items():
        if k.lower() == key.lower():
            return v
    return None
