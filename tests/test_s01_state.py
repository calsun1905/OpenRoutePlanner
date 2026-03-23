from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
STATE_PATH = ROOT / ".gsd" / "STATE.md"
STATE_EXAMPLE_PATH = ROOT / ".gsd" / "STATE.example.md"


def _resolve_state_path() -> Path:
    if STATE_PATH.exists():
        return STATE_PATH
    if STATE_EXAMPLE_PATH.exists():
        return STATE_EXAMPLE_PATH
    raise FileNotFoundError(
        "Missing state file. Expected .gsd/STATE.md or .gsd/STATE.example.md."
    )


def read_state() -> str:
    return _resolve_state_path().read_text(encoding="utf-8")


def test_state_contains_milestone_and_slice():
    s = read_state()
    assert "Active Milestone" in s, 'STATE file is missing "Active Milestone"'
    assert "M001" in s, 'STATE file is missing "M001"'
    assert "Active Slice" in s, 'STATE file is missing "Active Slice"'
    assert re.search(r"\bS\d+\b", s), 'STATE file is missing a slice id like "S01"'


def test_state_has_next_action_paragraph():
    s = read_state()
    assert "Next Action" in s, 'STATE file is missing "Next Action"'
    next_action_lines = [line.strip() for line in s.splitlines() if line.strip()]
    assert any("next action" in line.lower() for line in next_action_lines)


def test_state_md_has_required_fields():
    text = read_state()
    lowered = text.lower()
    required_tokens = ["active milestone", "active slice", "blockers", "next action"]
    missing = [token for token in required_tokens if token not in lowered]
    if (
        "active task" not in lowered
        and "open decisions" not in lowered
        and "recent decisions" not in lowered
    ):
        missing.append("active task/open decisions/recent decisions")
    assert not missing, f"Missing required STATE fields: {missing}"


def test_blockers_format():
    lines = read_state().splitlines()

    idx = None
    for i, line in enumerate(lines):
        normalized = line.strip().lower().strip("#").strip("*").strip()
        if normalized.startswith("blockers"):
            idx = i
            break
    assert idx is not None, 'Missing "Blockers:" heading'

    next_lines = [line.strip() for line in lines[idx + 1 : idx + 4]]
    if any(line.startswith("-") for line in next_lines):
        return

    assert any("none" in line.lower() for line in next_lines), (
        'Blockers list is malformed or missing items (use "- none" if no blockers)'
    )
