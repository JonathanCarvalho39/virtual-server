from __future__ import annotations

import json
from pathlib import Path

from models.scenario import Scenario


class ScenarioLoader:
    def load_all(self, scenarios_dir: Path) -> list[Scenario]:
        scenarios: list[Scenario] = []

        for json_file in sorted(scenarios_dir.glob("*.json")):
            scenario = self.load_one(json_file)
            if scenario is not None:
                scenarios.append(scenario)

        return scenarios

    def load_one(self, file_path: Path) -> Scenario | None:
        try:
            raw = json.loads(file_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return None

        raw["file_path"] = str(file_path)
        scenario = Scenario.model_validate(raw)
        scenario.compute_specificity()
        return scenario
