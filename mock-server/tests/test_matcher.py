from pathlib import Path

from models.scenario import Scenario
from services.matcher import match_request, select_scenario

API_DIR = Path(__file__).parent.parent / "api"


def _load_scenarios(method: str) -> list[Scenario]:
    from services.folder_scanner import FolderScanner
    from services.scenario_loader import ScenarioLoader

    scanner = FolderScanner(API_DIR)
    loader = ScenarioLoader()
    for route_path, m, scenarios_dir in scanner.scan():
        if m == method and "usuarios" in route_path:
            return loader.load_all(scenarios_dir)
    return []


def test_match_any_request():
    scenarios = _load_scenarios("GET")
    assert len(scenarios) > 0
    assert match_request(scenarios[0], {}, {}, None)


def test_match_missing_header():
    scenarios = _load_scenarios("GET")
    no_auth = [s for s in scenarios if "Autenticado" in s.name]
    assert len(no_auth) == 1
    assert match_request(no_auth[0], {}, {}, None)


def test_select_scenario_prefers_specific():
    scenarios = _load_scenarios("POST")
    body = {"cpf": "12345678901", "nome": "João"}
    selected = select_scenario(scenarios, {}, {}, body)
    assert selected is not None
    assert selected.name == "Criar Usuário - CPF Duplicado"


def test_select_scenario_fallback():
    scenarios = _load_scenarios("POST")
    body = {"cpf": "99999999999", "nome": "Maria"}
    selected = select_scenario(scenarios, {}, {}, body)
    assert selected is not None
    assert selected.name == "Criar Usuário - Sucesso"
