import json
from pathlib import Path

import pytest
from pytest_recap.models import TestSession


@pytest.mark.parametrize(
    "session_path",
    [pytest.param(str(p), id=p.name) for p in Path.home().joinpath(".pytest-recap-sessions").glob("*.json")],
)
def test_end_to_end_serialization(session_path):
    """End-to-end test: load, deserialize, serialize, and re-deserialize a real session file."""
    with open(session_path, "r") as f:
        session_dict = json.load(f)
    # Defensive: handle both list and dict top-level formats
    sessions = session_dict if isinstance(session_dict, list) else [session_dict]
    for orig in sessions:
        # Deserialize
        session = TestSession.from_dict(orig)
        # Serialize
        out_dict = session.to_dict()
        # Re-deserialize
        session2 = TestSession.from_dict(out_dict)
        # Compare dicts for round-trip fidelity
        assert out_dict == session2.to_dict(), f"Mismatch after round-trip for {session_path}"
        # Optionally, compare top-level fields
        assert session.session_id == session2.session_id
