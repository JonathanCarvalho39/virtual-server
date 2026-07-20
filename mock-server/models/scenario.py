from __future__ import annotations

import re
from enum import Enum
from typing import Any

from pydantic import BaseModel, field_validator


class RequestToken(str, Enum):
    ANY = "/any/"
    MISSING = "/missing/"
    NULL = "/null/"
    EMPTY = "/empty/"
    STRING = "/string/"
    NUMBER = "/number/"
    BOOLEAN = "/boolean/"
    ARRAY = "/array/"
    OBJECT = "/object/"
    UUID = "/uuid/"
    DATE = "/date/"


class ResponseToken(str, Enum):
    UUID = "/uuid/"
    NOW = "/now/"
    TIMESTAMP = "/timestamp/"
    RANDOM_INT = "/random/int/"
    RANDOM_STRING = "/random/string/"
    RANDOM_BOOLEAN = "/random/boolean/"


class RequestRules(BaseModel):
    headers: dict[str, str] = {}
    query: dict[str, str] = {}
    body: dict[str, Any] = {}

    @field_validator("headers", "query", "body", mode="before")
    @classmethod
    def default_empty(cls, v: Any) -> dict:
        return v or {}


class ResponseDef(BaseModel):
    status: int = 200
    headers: dict[str, str] = {}
    body: Any = {}

    @field_validator("headers", mode="before")
    @classmethod
    def default_empty(cls, v: Any) -> dict:
        return v or {}


class Scenario(BaseModel):
    name: str = ""
    request: RequestRules = RequestRules()
    response: ResponseDef = ResponseDef()
    file_path: str = ""
    specificity: int = 0

    def compute_specificity(self) -> int:
        count = 0
        for rules in (self.request.headers, self.request.query, self.request.body):
            for pattern in rules.values():
                if isinstance(pattern, str):
                    if is_regex(pattern):
                        count += 2
                    elif is_token(pattern):
                        count += 1
                    else:
                        count += 3
                else:
                    count += 3
        self.specificity = count
        return count


def is_regex(value: str) -> bool:
    return value.startswith("^") and value.endswith("$")


def is_token(value: str) -> bool:
    try:
        RequestToken(value)
        return True
    except ValueError:
        return False


def is_response_token(value: str) -> bool:
    if value.startswith("/random/int/"):
        return True
    if value.startswith("/random/string/"):
        return True
    try:
        ResponseToken(value)
        return True
    except ValueError:
        return False


def validate_regex(pattern: str) -> bool:
    try:
        re.compile(pattern)
        return True
    except re.error:
        return False
