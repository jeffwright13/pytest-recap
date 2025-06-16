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

    # If input is a list, treat as multiple sessions; else, single session
    sessions = data if isinstance(data, list) else [data]

    env = Environment(loader=FileSystemLoader(template_dir))
    template = env.get_template("report_template.html")

    def dedup(items):
        seen = set()
        unique = []
        for item in items:
            key = (item.get("nodeid"), item.get("message"))
            if key not in seen:
                seen.add(key)
                unique.append(item)
        return unique

    rendered_reports = []
    session_labels = []
    charts = []  # Collect chart info for each session
    for idx, data in enumerate(sessions):
        session = {
            "session_start_time": data.get("session_start_time"),
            "session_stop_time": data.get("session_stop_time"),
            "session_id": data.get("session_id"),
            "session_tags": data.get("session_tags"),
        }
        session_start = session["session_start_time"]
        session_stop = session["session_stop_time"]
        duration = None
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
        # Save chart info for this session
        charts.append({
            "labels": chart_labels,
            "data": chart_data,
            "colors": chart_colors,
        })
        # Render template for this session
        chart_id = f"pieChart" if len(sessions) == 1 else f"pieChart-{idx}"
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
            chart_id=chart_id,
        )
        rendered_reports.append(html)
        label = f"{session.get('session_id', 'Session '+str(idx+1))}"
        if session.get("session_start_time"):
            label += f" ({session['session_start_time']})"
        session_labels.append(label)

    # Compose outer HTML if multiple sessions
    if len(rendered_reports) == 1:
        # Single session: inject chartData and JS for chart rendering
        chart_id = "pieChart"
        chart_obj = charts[0]
        chart_data_js_obj = '{"pieChart": ' + json.dumps(chart_obj) + '}'
        js = f'''
<script>
var chartInstances = {{}};
var chartData = {chart_data_js_obj};
function initChart(chartId) {{
    if (chartInstances[chartId]) return;
    var ctx = document.getElementById(chartId).getContext('2d');
    var data = chartData[chartId];
    chartInstances[chartId] = new Chart(ctx, {{
        type: 'pie',
        data: {{
            labels: data.labels,
            datasets: [{{ data: data.data, backgroundColor: data.colors }}]
        }},
        options: {{ plugins: {{ legend: {{ position: 'right' }} }} }}
    }});
}}
window.addEventListener('DOMContentLoaded', function() {{
    var first = document.getElementById('{chart_id}');
    if (first) initChart(first.id);
}});
</script>
'''
        # Insert generated_at timestamp
        from datetime import datetime, timezone
        generated_at = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S %Z')
        # Insert JS and pass generated_at to template
        # Re-render the template with generated_at
        html = template.render(
            total=len(test_results),
            session=sessions[0],
            duration=duration,
            human_duration=human_duration,
            system_under_test=sessions[0].get("system_under_test", {}),
            testing_system=sessions[0].get("testing_system", {}),
            test_results=sessions[0].get("test_results", []),
            warnings=dedup(sessions[0].get("warnings", [])),
            errors=dedup(sessions[0].get("errors", [])),
            rerun_test_groups=[RerunTestGroup.from_dict(g) for g in sessions[0].get("rerun_test_groups", [])],
            chart=chart_obj,
            outcome_color_map=outcome_color_map,
            outcome_counts=outcome_counts,
            outcome_percentages=outcome_percentages,
            chart_id=chart_id,
            generated_at=generated_at,
        )
        # Insert JS before </body>
        if '</body>' in html:
            html = html.replace('</body>', js + '</body>')
        html_path.write_text(html, encoding="utf-8")
    else:
        # Compose dropdown and JS
        nav_html = [
            '<div class="session-nav-container">',
            '<label for="session-select" class="session-nav-label"><strong>Choose session:</strong></label>',
            '<select id="session-select" class="session-nav-select">'
        ]
        for idx, label in enumerate(session_labels):
            nav_html.append(f'<option value="session-{idx}">{label}</option>')
        nav_html.append('</select>')
        nav_html.append('</div>')
        # Wrap each report in a div
        # Add style block for modern dropdown
        style_block = '''<style>
.session-nav-container {
  display: flex;
  align-items: center;
  gap: 0.75em;
  margin: 1.5em 0 1.5em 0.5em;
}
.session-nav-label {
  font-weight: bold;
  font-size: 1.1em;
  letter-spacing: 0.01em;
  color: #333;
}
.session-nav-select {
  font-size: 1em;
  padding: 0.3em 1.1em 0.3em 0.7em;
  border-radius: 0.35em;
  border: 1px solid #aaa;
  background: #f7f7fa;
  color: #222;
  font-weight: 600;
  outline: none;
  transition: border 0.2s, box-shadow 0.2s;
  box-shadow: 0 1px 3px rgba(0,0,0,0.04);
}
.session-nav-select:focus {
  border: 1.5px solid #1976d2;
  box-shadow: 0 0 0 2px #1976d230;
}
</style>'''

        # Build chart data for each session directly from computed values
        chart_data_js = []
        for idx, chart in enumerate(charts):
            chart_id = f"pieChart" if len(charts) == 1 else f"pieChart-{idx}"
            chart_data_js.append(f'"{chart_id}": {json.dumps(chart)}')
        chart_data_js_obj = '{' + ','.join(chart_data_js) + '}'

        reports_html = []
        # Compute generated_at timestamp once for all sessions
        from datetime import datetime, timezone
        generated_at = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S %Z')
        # Re-render all reports with generated_at
        for idx, data in enumerate(sessions):
            style = "" if idx == 0 else "display:none;"
            # Recompute outcome_counts and outcome_percentages for this session
            test_results = data.get("test_results", [])
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
            total_tests = sum(outcome_counts.values()) or 1
            outcome_percentages = {k: int(round(100 * v / total_tests)) for k, v in outcome_counts.items()}
            report = template.render(
                total=len(test_results),
                session={
                    "session_start_time": data.get("session_start_time"),
                    "session_stop_time": data.get("session_stop_time"),
                    "session_id": data.get("session_id"),
                    "session_tags": data.get("session_tags"),
                },
                duration=None,  # Could be recomputed if needed
                human_duration=None,  # Could be recomputed if needed
                system_under_test=data.get("system_under_test", {}),
                testing_system=data.get("testing_system", {}),
                test_results=test_results,
                warnings=dedup(data.get("warnings", [])),
                errors=dedup(data.get("errors", [])),
                rerun_test_groups=[RerunTestGroup.from_dict(g) for g in data.get("rerun_test_groups", [])],
                chart=charts[idx],
                outcome_color_map=outcome_color_map,
                outcome_counts=outcome_counts,
                outcome_percentages=outcome_percentages,
                chart_id=f"pieChart" if len(charts) == 1 else f"pieChart-{idx}",
                generated_at=generated_at,
                session_idx=idx,
            )
            reports_html.append(f'<div id="session-{idx}" class="session-report" style="{style}">{report}</div>')
        # JS for switching and lazy chart initialization
        js = f'''
<script>
var chartInstances = {{}};
var chartData = {chart_data_js_obj};
var currentChart = null;
function initChart(chartId) {{
    if (chartInstances[chartId]) return; // Already initialized
    var ctx = document.getElementById(chartId).getContext('2d');
    var data = chartData[chartId];
    chartInstances[chartId] = new Chart(ctx, {{
        type: 'pie',
        data: {{
            labels: data.labels,
            datasets: [{{ data: data.data, backgroundColor: data.colors }}]
        }},
        options: {{ plugins: {{ legend: {{ position: 'right' }} }} }}
    }});
}}
document.getElementById('session-select').onchange = function() {{
    var val = this.value;
    document.querySelectorAll('.session-report').forEach(function(div) {{
        div.style.display = 'none';
    }});
    document.getElementById(val).style.display = '';
    var chartId = document.getElementById(val).querySelector('canvas').id;
    initChart(chartId);
}};
// Initialize the first chart on load
window.addEventListener('DOMContentLoaded', function() {{
    var first = document.querySelector('.session-report:not([style*="display:none"]) canvas');
    if (first) initChart(first.id);
}});
</script>
'''
        # Compose final HTML
        full_html = "\n".join([
            "<html><head><meta charset=\"utf-8\">",
            style_block,
            "</head><body>",
            *nav_html,
            *reports_html,
            js,
            "</body></html>"
        ])
        html_path.write_text(full_html, encoding="utf-8")
    print(f"Wrote report: {html_path}")


def main(json_path, html_path):
    render_report(Path(json_path), Path(html_path), Path("scripts/templates"))


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python recap_json_to_html.py <input.json> <output.html>")
        sys.exit(1)
    main(Path(sys.argv[1]), Path(sys.argv[2]))
