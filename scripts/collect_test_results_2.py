"""
collect_test_results_2.py (v2)

This script leverages the SiteBuilder API to:
- Download a build report for each build in SYSTEMS
- For each sucessful build in the report:
  - Download the pytest-html report
  - Parse it into a TestSession object
  - Save the TestSession object as a single JSON file

The mechanics are as follows:

1. For each system listed in SYSTEMS:
   a. Attempt to load cached build information from .cache/builds/{system}.json if it exists.
   b. If no cache is found or caching is disabled, download build information from the remote API using JWT authentication.
   c. Save newly downloaded build information to the cache for future runs.

2. Filter the retrieved builds for those where buildSuccessful is True and jenkinsStatus is 'Completed'.

3. For each successful and completed build:
   a. Attempt to load the cached pytest-html report from .cache/reports/{build_id}.html if it exists.
   b. If no cache is found or caching is disabled, download the pytest-html report from the remote API using JWT authentication.
   c. Save newly downloaded reports to the cache for future runs.
   d. Use robust error handling and retry logic for API requests (with exponential backoff on 503 errors and graceful handling of 404s).

4. Parse each pytest-html report into a TestSession object using the data model (via BeautifulSoup and custom logic).
   - Handle any malformed or incomplete reports gracefully, logging errors as needed.

5. Aggregate all TestSession objects into a single collection.

6. Save the aggregated TestSession collection as a JSON file.

7. Throughout the process:
   - Display progress to the user using rich.progress (spinner, bar, elapsed time, etc.).
   - Ensure required environment variables (e.g., SITEBUILDER_JWT_KEY) are set, raising clear errors if missing.
   - Create necessary cache directories if they do not exist.
   - Log warnings, errors, and summary statistics as appropriate.
"""

import time
import requests
import json
import os
from bs4 import BeautifulSoup
from typing import List, Dict, Optional, Callable
from pytest_pail.models_pytest_recap import TestSession, TestResult, TestOutcome, RerunTestGroup
import typer
from datetime import datetime, timedelta, timezone
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TimeElapsedColumn, TaskProgressColumn
import jsonschema

app = typer.Typer(help="Pytest session collection and utilities")

DEFAULT_OUTPUT_FILE = "all_test_sessions.json"
DEFAULT_CACHE_DIR = ".cache"
DEFAULT_BUILDS_SUBDIR = "builds"
DEFAULT_REPORTS_SUBDIR = "reports"
DEFAULT_MAX_REPORTS = 50

SYSTEMS = [
    {"name": "qa-jeff-dist-core-openjdk17-2"},
]

MAX_BUILDS_PER_SYSTEM = 50

def get_jwt_key() -> str:
    jwt = os.getenv("SITEBUILDER_JWT_KEY")
    if not jwt:
        raise RuntimeError("SITEBUILDER_JWT_KEY environment variable not set.")
    return jwt

def robust_request(
    request_fn: Callable[[], requests.Response],
    max_retries: int = 4,
    delay: int = 3,
    context: Optional[str] = None,
    not_found_message: Optional[str] = None,
) -> Optional[requests.Response]:
    retries = 0
    while retries <= max_retries:
        response = request_fn()
        if response.status_code == 200:
            return response
        elif response.status_code == 503 and retries < max_retries:
            wait = delay * (2 ** retries)
            if context:
                print(f"503 error {context}, retrying in {wait}s...")
            time.sleep(wait)
            retries += 1
            continue
        elif response.status_code == 404:
            if not_found_message:
                print(not_found_message)
            return None
        else:
            response.raise_for_status()
    if context:
        print(f"Failed after {max_retries} retries: {context or ''}")
    return None

class BuildFetcher:
    BASE_URL = "https://sitebuilder.sb.gems.energy"

    def __init__(self, jwt_key: str, cache: bool = True):
        self.jwt = jwt_key
        self.headers = {"Authorization": f"Bearer {self.jwt}"}
        self.cache = cache
        os.makedirs(CACHE_BUILDS_DIR, exist_ok=True)

    def fetch_builds(self, system_name: str, max_retries=4, delay=3) -> list:
        # Always redownload builds from API, ignore cache
        url = f"{self.BASE_URL}/api/v1/projects/{system_name}/builds"
        def req():
            return requests.get(url, headers=self.headers)
        response = robust_request(
            req,
            max_retries=max_retries,
            delay=delay,
            context=f"fetching builds for {system_name}",
            not_found_message=f"404 error: Project {system_name} not found."
        )
        builds = [] if response is None else response.json()
        # Optionally update cache for inspection, but never read from cache
        if self.cache and builds:
            try:
                cache_path = os.path.join(CACHE_BUILDS_DIR, f"{system_name}.json")
                with open(cache_path, "w") as f:
                    json.dump(builds, f)
            except Exception as e:
                print(f"Warning: Failed to cache builds for {system_name}: {e}")
        return builds

def download_pytest_html(build_id, jwt, dest_dir="reports", max_retries=3, delay=2, cache=True):
    os.makedirs(dest_dir, exist_ok=True)
    os.makedirs(CACHE_REPORTS_DIR, exist_ok=True)
    cache_path = os.path.join(CACHE_REPORTS_DIR, f"{build_id}.html")
    if cache and os.path.exists(cache_path):
        print(f"[INFO] Using cached HTML report for build {build_id}: {cache_path}")
        return cache_path
    url = f"https://sitebuilder.sb.gems.energy/api/v1/projects/project-builds/{build_id}/report/"
    headers = {"Authorization": f"Bearer {jwt}"}
    def req():
        return requests.get(url, headers=headers)
    response = robust_request(
        req,
        max_retries=max_retries,
        delay=delay,
        context=f"downloading report for build {build_id}",
        not_found_message=f"404 error for build {build_id}: report not found."
    )
    if response is None:
        raise Exception(f"Report for build {build_id} not found.")
    with open(cache_path, "wb") as f:
        f.write(response.content)
    time.sleep(delay)
    return cache_path

def group_tests_into_rerun_test_groups(
    test_results: List[TestResult],
) -> List[RerunTestGroup]:
    rerun_test_groups: Dict[str, RerunTestGroup] = {}
    for test_result in test_results:
        if test_result.nodeid not in rerun_test_groups:
            rerun_test_groups[test_result.nodeid] = RerunTestGroup(nodeid=test_result.nodeid, tests=[])
        rerun_test_groups[test_result.nodeid].tests.append(test_result)
    return list(rerun_test_groups.values())

def parse_pytest_html_report(
    html_path,
    system_under_test=None,
    session_id=None,
    build_id=None,
    system_info=None
):
    """
    Parse a pytest-html report and build a TestSession object using pytest_recap.models.
    Ensures all timestamps are timezone-aware UTC.
    """
    with open(html_path, "r") as f:
        html_content = f.read()
        if "The QA report is not available yet" in html_content:
            print(f"[WARN] Report at {html_path} is not available yet. Skipping.")
            return None
        soup = BeautifulSoup(html_content, "html.parser")

    # --- Extract test results ---
    test_results = []
    test_table = soup.find("table", {"id": "results-table"}) or soup.find("table", {"class": "results-table"})
    if test_table:
        for row in test_table.find_all("tr")[1:]:
            if not row.find("td", class_="col-result"):
                continue
            cells = row.find_all("td")
            if not cells or len(cells) < 3:
                continue
            outcome_str = cells[0].get_text(strip=True)
            nodeid = cells[1].get_text(strip=True)
            start_time = None
            stop_time = None
            duration_str = cells[2].get_text(strip=True)
            try:
                h, m, s = duration_str.split(":")
                duration = int(h) * 3600 + int(m) * 60 + float(s)
            except Exception:
                duration = None
            try:
                # If time present, make it timezone-aware UTC
                start_time = datetime.strptime(cells[4].get_text(strip=True), "%Y-%m-%d %H:%M:%S.%f").replace(tzinfo=timezone.utc)
            except Exception:
                start_time = datetime.now(timezone.utc)
            stop_time = start_time
            if duration is not None:
                stop_time = start_time + timedelta(seconds=duration)
            caplog = capstdout = capstderr = longreprtext = ""
            try:
                outcome = TestOutcome.from_str(outcome_str)
            except Exception:
                continue
            test_result = TestResult(
                nodeid=nodeid,
                outcome=outcome,
                start_time=start_time,
                stop_time=stop_time,
                duration=duration,
                caplog=caplog,
                capstdout=capstdout,
                capstderr=capstderr,
                longreprtext=longreprtext,
            )
            test_results.append(test_result)
    if test_results:
        session_start_time = min(tr.start_time for tr in test_results)
        session_stop_time = max(tr.stop_time for tr in test_results)
        session_duration = (session_stop_time - session_start_time).total_seconds()
    else:
        session_start_time = session_stop_time = datetime.now(timezone.utc)
        session_duration = 0.0
    rerun_groups = group_tests_into_rerun_test_groups(test_results)
    session_tags = {"session_duration": str(session_duration)}
    session = TestSession(
        system_under_test=system_under_test or {},
        session_id=session_id,
        session_start_time=session_start_time,
        session_stop_time=session_stop_time,
        session_tags=session_tags,
        test_results=test_results,
        rerun_test_groups=rerun_groups,
    )
    return session

@app.command()
def collect(
    output_file: str = typer.Option(DEFAULT_OUTPUT_FILE, "--output", help="Output JSON file for all sessions"),
    cache_dir: str = typer.Option(DEFAULT_CACHE_DIR, "--cache-dir", help="Root cache directory"),
    builds_subdir: str = typer.Option(DEFAULT_BUILDS_SUBDIR, "--builds-subdir", help="Builds cache subdirectory"),
    reports_subdir: str = typer.Option(DEFAULT_REPORTS_SUBDIR, "--reports-subdir", help="Reports cache subdirectory"),
    max_reports: int = typer.Option(DEFAULT_MAX_REPORTS, "--max-reports", help="Max number of reports/files to process"),
    json_output: bool = typer.Option(False, "--json", help="Output results as JSON to stdout"),
    no_cache: bool = typer.Option(False, "--no-cache", help="Disable local caching of builds and reports"),
    validate_schema: bool = typer.Option(True, "--validate/--no-validate", help="Validate output JSON against pytest-recap schema")
):
    """
    Main entry point for collecting test results, outputting JSON compliant with pytest-recap schema,
    and optionally validating output against the schema.
    """
    # Get JWT key from environment variable SITEBUILDER_JWT_KEY
    jwt = get_jwt_key()

    use_cache = not no_cache
    fetcher = BuildFetcher(jwt, cache=use_cache)
    all_sessions = []
    system_builds = []

    # Compose full cache paths
    builds_dir = os.path.join(cache_dir, builds_subdir)
    reports_dir = os.path.join(cache_dir, reports_subdir)
    os.makedirs(builds_dir, exist_ok=True)
    os.makedirs(reports_dir, exist_ok=True)

    processed = 0
    report_files = [f for f in os.listdir(reports_dir) if f.endswith('.html')][:max_reports]
    total_tasks = len(report_files)
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        TimeElapsedColumn(),
        transient=True
    ) as progress:
        task = progress.add_task(
            "Processing cached HTML reports", total=total_tasks
        )
        for fname in report_files:
            build_id = fname.replace('.html', '')
            html_path = os.path.join(reports_dir, fname)
            # Try to infer system name from build caches
            system_name = None
            for system in SYSTEMS:
                sysname = system["name"]
                build_cache_path = os.path.join(builds_dir, f"{sysname}.json")
                if os.path.exists(build_cache_path):
                    with open(build_cache_path, "r") as f:
                        builds = json.load(f)
                        if any(b.get("id") == build_id for b in builds):
                            system_name = sysname
                            break
            if not system_name:
                system_name = "unknown"
            try:
                session = parse_pytest_html_report(
                    html_path,
                    system_under_test={"name": system_name},
                    session_id=build_id
                )
                if session:
                    all_sessions.append(session)
            except Exception as e:
                print(f"Error processing cached report {fname} (build {build_id}) for {system_name}: {e}")
            processed += 1
            progress.update(task, advance=1, description=f"Processed {processed}/{total_tasks}")

    # Deduplicate sessions by session_id (last-in-wins)
    session_map = {}
    for s in all_sessions:
        if hasattr(s, 'session_id'):
            session_map[s.session_id] = s
        else:
            # Fallback: include session if no session_id
            session_map[id(s)] = s
    sessions_dict = [s.to_dict() for s in session_map.values()]

    # Schema validation
    if validate_schema:
        schema_path = os.path.join(os.path.dirname(__file__), "../pytest-recap/schema/pytest-recap-session.schema.json")
        try:
            with open(schema_path, "r") as schema_file:
                schema = json.load(schema_file)
            # Validate each session dict
            for i, session in enumerate(sessions_dict):
                jsonschema.validate(instance=session, schema=schema)
        except Exception as e:
            print(f"[ERROR] Schema validation failed: {e}")
            raise
        else:
            print("[INFO] All sessions validated successfully against pytest-recap schema.")

    with open(output_file, "w") as f:
        json.dump(sessions_dict, f, indent=2)
    if json_output:
        print(json.dumps(sessions_dict, indent=2))
    else:
        print(f"Saved {len(sessions_dict)} test sessions to {output_file}")


@app.command()
def deduplicate(
    input_file: str = typer.Argument(DEFAULT_OUTPUT_FILE, help="Input JSON file to deduplicate"),
    output_file: str = typer.Option("all_test_sessions.deduped.json", "--output", help="Deduplicated output JSON file")
):
    """
    Deduplicate a JSON file of test sessions by session_id. Keeps the last occurrence of each session_id.
    """
    with open(input_file, "r") as f:
        sessions = json.load(f)
    session_map = {}
    for s in sessions:
        sid = s.get("session_id")
        if sid is not None:
            session_map[sid] = s
        else:
            session_map[id(s)] = s
    deduped = list(session_map.values())
    with open(output_file, "w") as f:
        json.dump(deduped, f, indent=2)
    print(f"Deduplicated {len(sessions)} sessions to {len(deduped)} unique session_ids. Output: {output_file}")

if __name__ == "__main__":
    app()
