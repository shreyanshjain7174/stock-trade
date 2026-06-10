import json
import subprocess
import sys
from pathlib import Path


def test_local_ralph_smoke_exercises_loop_api_and_safety_gates(tmp_path) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    db_path = tmp_path / "ralph-smoke.db"

    result = subprocess.run(
        [
            sys.executable,
            "scripts/run_local_ralph_smoke.py",
            "--db-path",
            str(db_path),
            "--json",
        ],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
    )

    summary = json.loads(result.stdout)

    assert summary["run_id"] == "local-smoke"
    assert summary["event_count"] >= 4
    assert summary["plan_item_count"] > 0
    assert summary["health"]["mode"] == "research"
    assert summary["health"]["execution_enabled"] is False
    assert summary["api"]["runs_status"] == 200
    assert summary["api"]["run_status"] == 200
    assert summary["api"]["leaderboard_status"] == 200
    assert summary["api"]["trace_status"] == 200
    assert summary["api"]["paper_execute_without_confirmation"] == 403
    assert summary["api"]["paper_execute_with_confirmation"] == 403
    assert summary["submitted_order_count"] == 0
    assert summary["secret_marker_present"] is False