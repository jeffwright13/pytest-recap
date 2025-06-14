import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

from jinja2 import Environment, FileSystemLoader
from pytest_recap.models import RerunTestGroup


def format_human_duration(seconds: Optional[float]) -> str:
    if seconds is None:
        return "N/A"
    try:
        seconds = float(seconds)
    except Exception:
        return "N/A"
    if seconds < 10:
        return f"{seconds:.6f}s"
    minutes, s = divmod(int(seconds), 60)
    hours, m = divmod(minutes, 60)
    if hours > 0:
        return f"{hours}h {m}m {s}s"
    elif minutes > 0:
        return f"{m}m {s}s"
    else:
        return f"{s}s"


def render_report(json_path: Path, html_path: Path, template_dir: Path) -> None:
    with open(json_path, "r") as f:
        data = json.load(f)

    # Build session dict from root-level fields
    session = {
        "session_start_time": data.get("session_start_time"),
        "session_stop_time": data.get("session_stop_time"),
        "session_id": data.get("session_id"),
        "session_tags": data.get("session_tags"),
    }
    session_start = session["session_start_time"]
    session_stop = session["session_stop_time"]
    duration = None  # Always define
    if session_start and session_stop:
        try:
            duration = (datetime.fromisoformat(session_stop) - datetime.fromisoformat(session_start)).total_seconds()
            human_duration = format_human_duration(duration)
        except Exception:
            duration = None
            human_duration = "N/A"
    else:
        duration = None
        human_duration = "N/A"

    test_results = data.get("test_results", [])
    test_results.sort(key=lambda x: (x.get("outcome", ""), x.get("start_time", "")))
    outcome_counts = {}
    for result in test_results:
        outcome = result.get("outcome", "unknown")
        outcome_counts[outcome] = outcome_counts.get(outcome, 0) + 1
    outcome_counts = {k: v for k, v in outcome_counts.items() if v > 0}
    outcome_color_map = {
        "passed": "#aed581",
        "failed": "#ef9a9a",
        "skipped": "#ffcc80",
        "error": "#ce93d8",
        "xfailed": "#90caf9",
        "xpassed": "#80deea",
        "rerun": "#b0bec5",
        "unknown": "#eeeeee",
    }

    chart_labels = [k for k in outcome_color_map if k in outcome_counts]
    chart_data = [outcome_counts[o] for o in chart_labels]
    chart_colors = [outcome_color_map.get(o, outcome_color_map["unknown"]) for o in chart_labels]
    total_tests = sum(outcome_counts.values()) or 1
    outcome_percentages = {k: int(round(100 * v / total_tests)) for k, v in outcome_counts.items()}
    for result in test_results:
        dur = result.get("duration")
        result["human_duration"] = format_human_duration(dur) if dur is not None else "N/A"

    env = Environment(loader=FileSystemLoader(template_dir))
    template = env.get_template("report_template.html")

    # Deduplicate warnings and errors by (nodeid, message)
    def dedup(items):
        seen = set()
        unique = []
        for item in items:
            key = (item.get("nodeid"), item.get("message"))
            if key not in seen:
                seen.add(key)
                unique.append(item)
        return unique

    html = template.render(
        total=len(test_results),
        session=session,
        duration=duration,
        human_duration=human_duration,
        system_under_test=data.get("system_under_test", {}),
        testing_system=data.get("testing_system", {}),
        test_results=test_results,
        warnings=dedup(data.get("warnings", [])),
        errors=dedup(data.get("errors", [])),
        rerun_test_groups=[RerunTestGroup.from_dict(g) for g in data.get("rerun_test_groups", [])],
        chart={"labels": chart_labels, "data": chart_data, "colors": chart_colors},
        outcome_color_map=outcome_color_map,
        outcome_counts=outcome_counts,
        outcome_percentages=outcome_percentages,
    )

    html_path.write_text(html, encoding="utf-8")
    print(f"Wrote report: {html_path}")


def main(json_path, html_path):
    render_report(Path(json_path), Path(html_path), Path("scripts/templates"))


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python recap_json_to_html.py <input.json> <output.html>")
        sys.exit(1)
    main(Path(sys.argv[1]), Path(sys.argv[2]))
