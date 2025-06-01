#!/usr/bin/env python3
"""
recap_json_to_html.py

Convert a pytest-recap JSON session file to a simple HTML report.

Usage:
    python recap_json_to_html.py recap.json report.html

This script reads a recap.json file (as produced by pytest-recap) and generates
an HTML report summarizing the test session and results.
"""

import datetime
import json
import json as _json
import sys
from pathlib import Path
from pytest_recap.models import RerunTestGroup


def format_human_duration(seconds):
    seconds = int(round(seconds))
    h, h_rem = divmod(seconds, 3600)
    m, s = divmod(h_rem, 60)
    parts = []
    if h:
        parts.append(f"{h}h")
    if m or h:
        parts.append(f"{m}m")
    parts.append(f"{s}s")
    return " ".join(parts) if parts else "0s"

def render_rerun_group_table(groups: list[RerunTestGroup]) -> str:
    """Render a table of rerun test groups in HTML."""
    if not groups:
        return "<p>No rerun test groups.</p>"
    header = "<th>Group Id</th><th>Final Outcome</th><th>Num Reruns</th><th>Test Nodeids</th>"
    rows = ""
    for group in groups:
        try:
            group_obj = RerunTestGroup.from_dict(group)
            group_id = group_obj.nodeid
            final_outcome = group_obj.final_outcome if group_obj.final_outcome is not None else "[unknown]"
            if final_outcome == "rerun":
                breakpoint()
                print()
            num_reruns = sum(test.outcome.value.lower() == "rerun" for test in group_obj.tests)
            nodeids = sorted({test.nodeid for test in group_obj.tests})
        except Exception:
            group_id = group.get("nodeid", "[unknown]")
            final_outcome = "[error]"
            num_reruns = 0
            nodeids = []
        rows += (
            f"<tr><td>{group_id}</td>"
            f"<td>{final_outcome}</td>"
            f"<td>{num_reruns}</td>"
            f"<td>{', '.join(nodeids)}</td></tr>\n"
        )
    return f"<table><thead><tr>{header}</tr></thead><tbody>{rows}</tbody></table>"

def main(json_path: Path, html_path: Path):
    """Convert recap.json to an advanced HTML report with summary stats, chart, sortable and expandable table.

    Args:
        json_path (Path): Path to the recap.json file.
        html_path (Path): Path to output HTML file.
    """
    with open(json_path, "r", encoding="utf-8") as f:
        data: dict = json.load(f)

    session: dict = data.get("session", {})
    session_start: str | None = session.get("session_start_time")
    session_stop: str | None = session.get("session_stop_time")
    session_duration: float = 0.0
    human_duration: str = "0s"
    if session_start and session_stop:
        try:
            start_dt = datetime.datetime.fromisoformat(session_start)
            stop_dt = datetime.datetime.fromisoformat(session_stop)
            session_duration = max((stop_dt - start_dt).total_seconds(), 0.0)
            human_duration = format_human_duration(session_duration)
        except Exception:
            session_duration = 0.0
            human_duration = "N/A"
    else:
        human_duration = "N/A"

    test_results: list[dict] = data.get("test_results", [])
    system_under_test: dict = data.get("system_under_test", {})
    testing_system: dict = data.get("testing_system", {})

    # --- Summary stats ---
    outcome_counts: dict[str, int] = {}
    for test_result in test_results:
        outcome = test_result.get("outcome", "unknown")
        outcome_counts[outcome] = outcome_counts.get(outcome, 0) + 1
    total = len(test_results)
    passed = outcome_counts.get("passed", 0)
    failed = outcome_counts.get("failed", 0)
    skipped = outcome_counts.get("skipped", 0)
    error = outcome_counts.get("error", 0)
    xfailed = outcome_counts.get("xfailed", 0)
    xpassed = outcome_counts.get("xpassed", 0)
    rerun = outcome_counts.get("rerun", 0)

    # --- Chart.js data ---
    chart_labels: list[str] = []
    chart_data: list[int] = []
    chart_colors: list[str] = []
    outcome_color_map: dict[str, str] = {
        "passed": "#4CAF50",
        "failed": "#F44336",
        "skipped": "#FF9800",
        "error": "#9C27B0",
        "xfailed": "#2196F3",
        "xpassed": "#00BCD4",
        "rerun": "#607D8B",
        "unknown": "#BDBDBD",
    }
    for outcome, count in outcome_counts.items():
        chart_labels.append(outcome)
        chart_data.append(count)
        chart_colors.append(outcome_color_map.get(outcome, "#BDBDBD"))

    # --- Warnings and Errors sections ---
    warnings: list[dict] = []
    errors: list[dict] = []
    # Collect events from 'warnings' and 'errors' arrays if present
    for event in data.get("warnings", []):
        if event.get("event_type", "warning") == "warning":
            warnings.append(event)
        elif event.get("event_type") == "error":
            errors.append(event)
    for event in data.get("errors", []):
        if event.get("event_type", "error"):
            errors.append(event)
        elif event.get("event_type") == "warning":
            warnings.append(event)

    def render_event_table(events, title):
        if not events:
            return f"<p>No {title.lower()}s.</p>"
        cols = ["nodeid", "when", "message", "category", "filename", "lineno", "outcome", "longrepr"]
        header = "".join(f"<th>{col.title()}</th>" for col in cols)
        rows = ""
        for ev in events:
            rows += "<tr>" + "".join(f"<td>{ev.get(col, '')}</td>" for col in cols) + "</tr>\n"
        return f"""
<table>
  <thead><tr>{header}</tr></thead>
  <tbody>
    {rows}
  </tbody>
</table>
"""

    # --- Rerun Test Groups section ---
    rerun_test_groups: list[dict] = data.get("rerun_test_groups", [])
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>pytest-recap Test Report</title>
  <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
  <style>
    body {{ font-family: sans-serif; margin: 2em; }}
    table {{ border-collapse: collapse; width: 100%; table-layout: fixed; }}
    th, td {{ border: 1px solid #ccc; padding: 0.5em; overflow-wrap: break-word; word-break: break-word; }}
    th {{ background: #f4f4f4; cursor: pointer; text-align: left; }}
    .test-title-cell {{ cursor: pointer; text-decoration: underline; color: #1976d2; width: 27em; min-width: 18em; }}
    .test-title-cell:hover {{ background: #f0f7ff; }}
    .col-outcome, .col-duration {{ width: 6em; min-width: 4em; }}

    .details-row td {{ max-width: none; word-break: break-word; }}
    .details-row pre {{ white-space: pre-wrap; word-break: break-word; max-width: none; overflow-x: auto; }}
    # tr.passed  {{ background: #e6f0db; }}
    # tr.failed  {{ background: #ffe5e7; }}
    # tr.skipped {{ background: #ffeed9; }}
    # tr.error   {{ background: #f3e5f5; }}
    # tr.xfailed {{ background: #e3f2fb; }}
    # tr.xpassed {{ background: #d8f5f7; }}
    # tr.rerun   {{ background: #e3e8eb; }}
    # tr.unknown {{ background: #f8f8f8; }}
    tr.passed  {{}}
    tr.failed  {{}}
    tr.skipped {{}}
    tr.error   {{}}
    tr.xfailed {{}}
    tr.xpassed {{}}
    tr.rerun   {{}}
    tr.unknown {{}}
    .outcome-dot {{ display:inline-block; width:12px; height:12px; border-radius:50%; margin-right:6px; }}
    .expand-btn {{ cursor: pointer; color: #1976d2; text-decoration: underline; }}
    .details-row {{ display: none; background: #f9f9f9; }}
    .summary-stats {{ margin-bottom: 2em; }}
    .pie-chart-container {{ width: 320px; margin: 1em 0; }}
  </style>
</head>
<body>
  <h1>pytest-recap Test Report</h1>
  <div class="summary-stats" style="display: flex; align-items: flex-start; gap: 2em;">
    <div>
      <h2>Summary</h2>
      <div style="margin-bottom: 0.5em; font-size: 1.1em;">
        {total} tests ran in {session_duration} seconds ({human_duration})
      </div>
      <ul>
        <li><strong>Total:</strong> {total}</li>
        <li><span class="outcome-dot" style="background:{outcome_color_map["passed"]}"></span> <strong>Passed:</strong> {passed}</li>
        <li><span class="outcome-dot" style="background:{outcome_color_map["failed"]}"></span> <strong>Failed:</strong> {failed}</li>
        <li><span class="outcome-dot" style="background:{outcome_color_map["skipped"]}"></span> <strong>Skipped:</strong> {skipped}</li>
        <li><span class="outcome-dot" style="background:{outcome_color_map["error"]}"></span> <strong>Error:</strong> {error}</li>
        <li><span class="outcome-dot" style="background:{outcome_color_map["xfailed"]}"></span> <strong>XFailed:</strong> {xfailed}</li>
        <li><span class="outcome-dot" style="background:{outcome_color_map["xpassed"]}"></span> <strong>XPassed:</strong> {xpassed}</li>
        <li><span class="outcome-dot" style="background:{outcome_color_map["rerun"]}"></span> <strong>Rerun:</strong> {rerun}</li>
      </ul>
    </div>
    <div class="pie-chart-container">
      <canvas id="pieChart"></canvas>
    </div>
  </div>
  <details>
    <summary><strong>Session Metadata</strong></summary>
    <ul>
      <li><strong>Session start:</strong> {session_start}</li>
      <li><strong>Session stop:</strong> {session_stop}</li>
      <li><strong>Duration:</strong> {session_duration} seconds</li>
      <li><strong>System Under Test:</strong> {system_under_test.get("name", "")}</li>
      <li><strong>Host:</strong> {testing_system.get("hostname", "")}</li>
      <li><strong>Platform:</strong> {testing_system.get("platform", "")}</li>
      <li><strong>Python:</strong> {testing_system.get("python_version", "")}</li>
      <li><strong>Pytest:</strong> {testing_system.get("pytest_version", "")}</li>
      <li><strong>Environment:</strong> {testing_system.get("environment", "")}</li>
    </ul>
  </details>

  <details>
    <summary><strong>Warnings ({len(warnings)})</strong></summary>
    {render_event_table(warnings, "Warning")}
  </details>
  <details>
    <summary><strong>Errors ({len(errors)})</strong></summary>
    {render_event_table(errors, "Error")}
  </details>

  <details>
    <summary><strong>Rerun Test Groups ({len(rerun_test_groups)})</strong></summary>
    {render_rerun_group_table(rerun_test_groups)}
  </details>

  <h2>Test Results</h2>
  <div id="outcome-filters" style="margin-bottom: 1em;">
    <strong>Show outcomes:</strong>
    <label><input type="checkbox" id="filter-all" checked> All</label>
    <label><input type="checkbox" class="filter-checkbox" value="passed" checked> Passed</label>
    <label><input type="checkbox" class="filter-checkbox" value="failed" checked> Failed</label>
    <label><input type="checkbox" class="filter-checkbox" value="skipped" checked> Skipped</label>
    <label><input type="checkbox" class="filter-checkbox" value="error" checked> Error</label>
    <label><input type="checkbox" class="filter-checkbox" value="xfailed" checked> XFailed</label>
    <label><input type="checkbox" class="filter-checkbox" value="xpassed" checked> XPassed</label>
    <label><input type="checkbox" class="filter-checkbox" value="rerun" checked> Rerun</label>
    <label><input type="checkbox" class="filter-checkbox" value="unknown" checked> Unknown</label>
  </div>
  <table id="results-table">
    <thead>
    <tr>
      <th>Test</th>
      <th class="col-outcome">Outcome</th>
      <th class="col-duration">Duration (s)</th>
      <th>Start</th>
      <th>Stop</th>
    </tr>
    </thead>
    <tbody>
"""

    # Sort: failures first, then errors, then others
    def sort_key(test_result):
        order = {"failed": 0, "error": 1, "xfailed": 2, "xpassed": 3, "rerun": 4, "skipped": 5, "passed": 6}
        return order.get(test_result.get("outcome", "unknown"), 99)

    test_results_sorted = sorted(test_results, key=sort_key)
    for idx, test_result in enumerate(test_results_sorted):
        outcome = test_result.get("outcome", "unknown")
        nodeid = test_result.get("nodeid", "")
        duration = test_result.get("duration", "")
        start_time = test_result.get("start_time", "")
        stop_time = test_result.get("stop_time", "")
        try:
            duration_fmt = f"{float(duration)}"
        except Exception:
            duration_fmt = duration

        capstdout = test_result.get("capstdout", "")
        capstderr = test_result.get("capstderr", "")
        caplog = test_result.get("caplog", "")
        longreprtext = test_result.get("longreprtext", "")
        row_id = f"details-{idx}"

        html += f'''    <tr class="{outcome}">
          <td class="test-title-cell" onclick="toggleDetails('{row_id}')">{nodeid}</td>
          <td class="col-outcome"><span class="outcome-dot" style="background:{outcome_color_map.get(outcome, "#BDBDBD")}"></span>{outcome}</td>
          <td class="col-duration">{duration_fmt}</td>
          <td>{start_time}</td>
          <td>{stop_time}</td>
        </tr>\n'''

        html += f'''    <tr id="{row_id}" class="details-row">
          <td colspan="5">
            <strong>Captured stdout:</strong><pre>{capstdout or "(none)"}</pre>
            <strong>Captured stderr:</strong><pre>{capstderr or "(none)"}</pre>
            <strong>Captured log:</strong><pre>{caplog or "(none)"}</pre>
            <strong>Error/Traceback:</strong><pre>{longreprtext or "(none)"}</pre>
          </td>
        </tr>\n'''
    html += """    </tbody>
  </table>
  <script>
    // Pie chart
    const ctx = document.getElementById('pieChart').getContext('2d');
    new Chart(ctx, {
      type: 'pie',
      data: {
        labels: %s,
        datasets: [{
          data: %s,
          backgroundColor: %s
        }]
      },
      options: {
        plugins: {
          legend: { position: 'right' }
        }
      }
    });

    // Expand/collapse details
    function toggleDetails(rowId) {
      var row = document.getElementById(rowId);
      if (!row) return;
      // Optionally, close others for clarity
      document.querySelectorAll('.details-row').forEach(r => {
        if (r.id !== rowId) r.style.display = 'none';
      });
      if (row.style.display === 'table-row') {
        row.style.display = 'none';
      } else {
        row.style.display = 'table-row';
      }
    }

    // Sortable table (click headers)
    document.querySelectorAll('#results-table th').forEach((header, idx) => {
      header.addEventListener('click', () => sortTable(idx));
    });
    function sortTable(colIdx) {
      var table = document.getElementById('results-table');
      var rows = Array.from(table.tBodies[0].rows).filter(r => !r.classList.contains('details-row'));
      var detailsRows = Array.from(table.tBodies[0].rows).filter(r => r.classList.contains('details-row'));
      rows.sort((a, b) => {
        var aText = a.cells[colIdx].innerText;
        var bText = b.cells[colIdx].innerText;
        if (colIdx === 2) { // duration numeric
          return parseFloat(bText) - parseFloat(aText);
        }
        return aText.localeCompare(bText);
      });
      // Remove all rows
      while (table.tBodies[0].firstChild) table.tBodies[0].removeChild(table.tBodies[0].firstChild);
      // Re-add in sorted order, pairing each data row with its details
      for (const row of rows) {
        table.tBodies[0].appendChild(row);
        var rowId = row.querySelector('.expand-btn')?.getAttribute('onclick')?.match(/'([^']+)'/);
        if (rowId) {
          var details = document.getElementById(rowId[1]);
          if (details) table.tBodies[0].appendChild(details);
        }
      }
    }

    // Outcome filter checkboxes
    const allBox = document.getElementById('filter-all');
    const filterBoxes = Array.from(document.querySelectorAll('.filter-checkbox'));
    function updateAllBox() {
      allBox.checked = filterBoxes.every(cb => cb.checked);
      allBox.indeterminate = !allBox.checked && filterBoxes.some(cb => cb.checked);
    }
    allBox.addEventListener('change', function() {
      filterBoxes.forEach(cb => { cb.checked = allBox.checked; });
      filterRows();
    });
    filterBoxes.forEach(cb => {
      cb.addEventListener('change', function() {
        updateAllBox();
        filterRows();
      });
    });
    function filterRows() {
      var show = {};
      filterBoxes.forEach(box => { show[box.value] = box.checked; });
      document.querySelectorAll('#results-table tbody tr').forEach(row => {
        if (row.classList.contains('details-row')) {
          var prev = row.previousElementSibling;
          row.style.display = (prev && prev.style.display !== 'none') ? row.style.display : 'none';
        } else {
          row.style.display = show[row.className] ? '' : 'none';
        }
      });
    }
    updateAllBox(); // initialize
    filterRows(); // initialize

  </script>
</body>
</html>
""" % (_json.dumps(chart_labels), _json.dumps(chart_data), _json.dumps(chart_colors))
    Path(html_path).write_text(html, encoding="utf-8")
    print(f"HTML report written to {html_path}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python recap_json_to_html.py <recap.json> <report.html>")
        sys.exit(1)
    main(Path(sys.argv[1]), Path(sys.argv[2]))
