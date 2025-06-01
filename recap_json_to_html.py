import json
import sys
from datetime import datetime
from pathlib import Path

from jinja2 import Environment, FileSystemLoader
from pytest_recap.models import RerunTestGroup


def format_human_duration(seconds: float) -> str:
    seconds = int(round(seconds))
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    return " ".join(f"{v}{u}" for v, u in zip((h, m, s), "hms") if v) or "0s"


def render_report(json_path: Path, html_path: Path, template_dir: Path) -> None:
    with open(json_path, "r") as f:
        data = json.load(f)

    session = data.get("session", {})
    test_results = data.get("test_results", [])
    test_results.sort(key=lambda x: (x.get("outcome", ""), x.get("start_time", "")))
    try:
        start = session.get("session_start_time")
        stop = session.get("session_stop_time")
        if start and stop:
            duration = max((datetime.fromisoformat(stop) - datetime.fromisoformat(start)).total_seconds(), 0.0)
            human_duration = format_human_duration(duration)
        else:
            raise ValueError("Missing timestamps")
    except Exception:
        duration, human_duration = 0.0, "N/A"

    outcome_counts = {}
    for result in test_results:
        outcome = result.get("outcome", "unknown")
        outcome_counts[outcome] = outcome_counts.get(outcome, 0) + 1

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

    env = Environment(loader=FileSystemLoader(template_dir))
    template = env.get_template("report_template.html")

    html = template.render(
        total=len(test_results),
        session=session,
        duration=duration,
        human_duration=human_duration,
        system_under_test=data.get("system_under_test", {}),
        testing_system=data.get("testing_system", {}),
        test_results=test_results,
        warnings=data.get("warnings", []),
        errors=data.get("errors", []),
        rerun_test_groups=[RerunTestGroup.from_dict(g) for g in data.get("rerun_test_groups", [])],
        chart={"labels": chart_labels, "data": chart_data, "colors": chart_colors},
        outcome_color_map=outcome_color_map,
        outcome_counts=outcome_counts,
    )

    html_path.write_text(html, encoding="utf-8")
    print(f"Wrote report: {html_path}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python recap_json_to_html.py recap.json report.html")
        sys.exit(1)
    render_report(Path(sys.argv[1]), Path(sys.argv[2]), Path("templates"))
