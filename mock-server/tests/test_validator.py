from pathlib import Path

from services.folder_scanner import FolderScanner
from services.scenario_loader import ScenarioLoader
from services.validator import Validator

API_DIR = Path(__file__).parent.parent / "api"


def test_validate_valid_project():
    scanner = FolderScanner(API_DIR)
    loader = ScenarioLoader()
    validator = Validator(scanner, loader)
    result = validator.validate_all()
    assert result.is_valid


def test_validate_invalid_regex():
    import json
    import tempfile
    import os

    bad_dir = Path(tempfile.mkdtemp()) / "api" / "test" / "get"
    bad_dir.mkdir(parents=True)
    bad_file = bad_dir / "bad.json"
    bad_file.write_text(json.dumps({
        "request": {"body": {"cpf": "^[0-9{11}$"}},
        "response": {"status": 200, "body": {}}
    }))

    scanner = FolderScanner(bad_dir.parent.parent)
    loader = ScenarioLoader()
    validator = Validator(scanner, loader)
    result = validator.validate_all()
    assert not result.is_valid

    os.remove(bad_file)
    os.rmdir(bad_dir)
    os.rmdir(bad_dir.parent)
    os.rmdir(bad_dir.parent.parent)
