from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .context import RuleSet


DEFAULT_RULES_PATH = (
    Path(__file__).resolve().parents[2]
    / "rules"
    / "oiml"
    / "R76"
    / "2006"
)


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Rules file not found: {path}")

    with path.open("r", encoding="utf-8") as file:
        data = json.load(file)

    if not isinstance(data, dict):
        raise ValueError(f"Rules file must contain a JSON object: {path}")

    return data


def load_r76_rules(
    rules_path: Path | str = DEFAULT_RULES_PATH,
) -> RuleSet:
    """
    Load the OIML R76-1:2006 prototype ruleset from JSON files.
    """

    rules_path = Path(rules_path)

    manifest = _load_json(rules_path / "manifest.json")
    tests = _load_json(rules_path / "tests.json")
    mpe_rules = _load_json(rules_path / "mpe_rules.json")
    applicability = _load_json(rules_path / "applicability.json")
    requirements = _load_json(rules_path / "requirements.json")
    calculations = _load_json(rules_path / "calculations.json")

    ruleset_version = manifest.get("ruleset_version")

    if not ruleset_version:
        raise ValueError("manifest.json is missing ruleset_version")

    return RuleSet(
        ruleset_version=ruleset_version,
        tests=tests,
        mpe_rules=mpe_rules,
        applicability=applicability,
        requirements=requirements,
        calculations=calculations,
    )