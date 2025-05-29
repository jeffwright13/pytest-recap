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


def format_human_duration(seconds):
    seconds = int(round(seconds))
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    parts = []
    if h:
        parts.append(f"{h}h")
    if m or h:
        parts.append(f"{m}m")
    parts.append(f"{s}s")
    return "".join(parts)


def main(json_path, html_path):
    """Convert recap.json to an advanced HTML report with summary stats, chart, sortable and expandable table.

    Args:
        json_path (str): Path to the recap.json file.
        html_path (str): Path to output HTML file.
    """
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    session = data.get("session", {})
    session_start = session.get("start") or data.get("session_start_time") or ""
    session_stop = session.get("stop") or data.get("session_stop_time") or ""
    # Calculate session duration (in seconds, 3 decimals)
    session_duration = 0.0
    human_duration = format_human_duration(session_duration)
    try:
        if session_start and session_stop:
            fmt = "%Y-%m-%dT%H:%M:%S"
            s_start = session_start.split(".")[0]
            s_stop = session_stop.split(".")[0]
            dt_start = datetime.datetime.strptime(s_start, fmt)
            dt_stop = datetime.datetime.strptime(s_stop, fmt)
            session_duration = (dt_stop - dt_start).total_seconds()
    except Exception:
        pass

    test_results = data.get("test_results", [])
    system_under_test = data.get("system_under_test", {})
    testing_system = data.get("testing_system", {})

    # --- Summary stats ---
    outcome_counts = {}
    for tr in test_results:
        outcome = tr.get("outcome", "unknown")
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
    chart_labels = []
    chart_data = []
    chart_colors = []
    outcome_color_map = {
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
    warnings = []
    errors = []
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
    rerun_test_groups = data.get("rerun_test_groups", [])

    def render_rerun_group_table(groups):
        if not groups:
            return "<p>No rerun test groups.</p>"
        header = "<th>Group Id</th><th>Final Outcome</th><th>Num Reruns</th><th>Test Nodeids</th>"
        rows = ""
        for g in groups:
            group_id = g.get("nodeid", "[unknown]")
            tests = g.get("tests", [])
            final_outcome = tests[-1].get("outcome") if tests else "[unknown]"
            num_reruns = sum(1 for t in tests if t.get("outcome") == "rerun")
            nodeids = sorted(set(t.get("nodeid", "") for t in tests))
            rows += (
                f"<tr><td>{group_id}</td>"
                f"<td>{final_outcome}</td>"
                f"<td>{num_reruns}</td>"
                f"<td>{', '.join(nodeids)}</td></tr>\n"
            )
        return f"<table><thead><tr>{header}</tr></thead><tbody>{rows}</tbody></table>"

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

    .details-row td {{ max-width: 800px; word-break: break-word; }}
    .details-row pre {{ white-space: pre-wrap; word-break: break-word; max-width: 800px; overflow-x: auto; }}
    tr.passed {{ background: #e8f5e9; }}
    tr.failed {{ background: #ffebee; }}
    tr.skipped {{ background: #fff8e1; }}
    tr.error {{ background: #f3e5f5; }}
    tr.xfailed {{ background: #e3f2fd; }}
    tr.xpassed {{ background: #e0f7fa; }}
    tr.rerun {{ background: #eceff1; }}
    tr.unknown {{ background: #f5f5f5; }}
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
        {total} tests ran in {session_duration:.3f} seconds ({human_duration})
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
      <li><strong>Duration:</strong> {session_duration:.3f} seconds</li>
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
    def sort_key(tr):
        order = {"failed": 0, "error": 1, "xfailed": 2, "xpassed": 3, "rerun": 4, "skipped": 5, "passed": 6}
        return order.get(tr.get("outcome", "unknown"), 99)

    test_results_sorted = sorted(test_results, key=sort_key)
    for idx, tr in enumerate(test_results_sorted):
        outcome = tr.get("outcome", "unknown")
        nodeid = tr.get("nodeid", "")
        duration = tr.get("duration", "")
        start_time = tr.get("start_time", "")
        stop_time = tr.get("stop_time", "")
        # Format duration to 3 decimals
        try:
            duration_fmt = f"{float(duration):.3f}"
        except Exception:
            duration_fmt = duration
        # Use full ISO timestamps for start/stop times
        start_time_fmt = start_time
        stop_time_fmt = stop_time

        capstdout = tr.get("capstdout", "")
        capstderr = tr.get("capstderr", "")
        caplog = tr.get("caplog", "")
        longreprtext = tr.get("longreprtext", "")
        row_id = f"details-{idx}"
        html += f'''    <tr class="{outcome}">
      <td class="test-title-cell" onclick="toggleDetails('{row_id}')">{nodeid}</td>
      <td class="col-outcome"><span class="outcome-dot" style="background:{outcome_color_map.get(outcome, "#BDBDBD")}"></span>{outcome}</td>
      <td class="col-duration">{duration_fmt}</td>
      <td>{start_time_fmt}</td>
      <td>{stop_time_fmt}</td>
    </tr>\n'''
        # Details row (hidden by default)
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
          legend: { position: 'bottom' }
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
    main(sys.argv[1], sys.argv[2])
