from services.matcher import (
    _match_token,
    _match_regex,
    _resolve_tokens,
)
from models.scenario import RequestToken, ResponseToken


def test_match_any_token():
    assert _match_token("/any/", "hello")
    assert _match_token("/any/", 123)
    assert not _match_token("/any/", None)


def test_match_missing_token():
    assert _match_token("/missing/", None)
    assert not _match_token("/missing/", "value")


def test_match_number_token():
    assert _match_token("/number/", 42)
    assert _match_token("/number/", 3.14)
    assert not _match_token("/number/", "42")


def test_match_regex():
    assert _match_regex("^[0-9]{11}$", "12345678901")
    assert not _match_regex("^[0-9]{11}$", "12345")


def test_resolve_uuid():
    result = _resolve_tokens("/uuid/", {}, {}, {})
    assert len(result) == 36
    assert "-" in result


def test_resolve_now():
    result = _resolve_tokens("/now/", {}, {}, {})
    assert "T" in result


def test_resolve_placeholder():
    body = {"nome": "João"}
    result = _resolve_tokens("{{request.body.nome}}", {}, {}, body)
    assert result == "João"
