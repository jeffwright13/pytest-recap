import glob
import json
from pathlib import Path
from typing import List

import typer
from pytest_recap.models import TestSession

app = typer.Typer()


def load_sessions_from_file(filepath: str) -> List[TestSession]:
    """Load a list of TestSession objects from a JSON file. Accepts either a list or a single session dict."""
    with open(filepath, "r") as f:
        data = json.load(f)
    if isinstance(data, list):
        return [TestSession.from_dict(item) for item in data]
    elif isinstance(data, dict):
        # Accept a single session dict as a one-item list
        return [TestSession.from_dict(data)]
    else:
        raise ValueError(f"Expected a list or dict in {filepath}, got {type(data)}")


def clean_empty_structs(obj):
    if isinstance(obj, dict):
        if not obj:
            return None
        return {k: clean_empty_structs(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        if not obj:
            return None
        return [clean_empty_structs(i) for i in obj]
    else:
        return obj


def serialize_nested_fields(session):
    # These are the fields expected to be JSON strings for Parquet compatibility
    for key in ["test_results", "rerun_test_groups", "session_tags", "testing_system"]:
        if key in session and not isinstance(session[key], str):
            session[key] = json.dumps(session[key])
    return session


@app.command()
def merge_sessions(
    input_glob: str = typer.Option(None, help='Glob pattern for input JSON files (default: "*.json")'),
    input_files: str = typer.Option(None, help="Comma-separated list of input JSON files"),
    input_dir: str = typer.Option(".", help="Directory to search for JSON files"),
    recurse: bool = typer.Option(
        False, "--recurse/--no-recurse", help="Recursively search input_dir for files (default: False)"
    ),
    output_parquet: str = typer.Option(None, help="Output Parquet file path"),
    output_json: str = typer.Option(None, help="Output JSON file path"),
):
    """
    Merge all TestSession JSON files, deduplicate by session_id, and export to Parquet and/or JSON.
    Accepts either a glob pattern or a comma-separated list of files.
    If only input_dir is given, merges all .json files (non-recursive by default).
    """
    files = []
    if input_files:
        files = [f.strip() for f in input_files.split(",") if f.strip()]
    else:
        # Determine glob pattern
        pattern = input_glob or "*.json"
        if recurse:
            # Use **/ for recursive glob
            search_path = (
                str(Path(input_dir) / "**" / pattern)
                if not pattern.startswith("**/")
                else str(Path(input_dir) / pattern)
            )
            files = glob.glob(search_path, recursive=True)
        else:
            search_path = str(Path(input_dir) / pattern)
            files = glob.glob(search_path, recursive=False)
    if not files:
        typer.secho(
            f"No input files found with pattern '{input_glob or '*.json'}' in {input_dir} (recurse={recurse})",
            fg=typer.colors.RED,
        )
        raise typer.Exit(code=1)

    typer.echo(f"Found {len(files)} files: {files}")
    all_sessions: List[TestSession] = []
    for file in files:
        try:
            sessions = load_sessions_from_file(file)
            all_sessions.extend(sessions)
        except Exception as e:
            typer.secho(f"Error loading {file}: {e}", fg=typer.colors.RED)

    session_map = {}
    duplicates = 0
    for session in all_sessions:
        # Defensive: convert any dicts to TestSession
        if isinstance(session, dict):
            session = TestSession.from_dict(session)
        session_id = getattr(session, "session_id", None)
        if session_id is None:
            typer.secho(f"Session missing 'session_id': {session}", fg=typer.colors.YELLOW)
            continue
        if session_id in session_map:
            duplicates += 1
            typer.secho(f"Duplicate session_id found: {session_id}", fg=typer.colors.RED)
            typer.echo(f"  Previous: {session_map[session_id]}")
            typer.echo(f"  Current:  {session}")
        else:
            session_map[session_id] = session

    typer.echo(f"Total sessions loaded: {len(all_sessions)}")
    typer.echo(f"Unique sessions: {len(session_map)}")
    typer.echo(f"Duplicates found: {duplicates}")

    # Ensure all sessions in session_map are TestSession objects
    session_map = {k: TestSession.from_dict(v) if isinstance(v, dict) else v for k, v in session_map.items()}

    # Validate round-trip serialization for all sessions
    round_trip_ok = True
    for s in session_map.values():
        try:
            d = s.to_dict()
            TestSession.from_dict(d)  # Should not raise
        except Exception as e:
            typer.secho(
                f"Round-trip serialization failed for session {getattr(s, 'session_id', None)}: {e}",
                fg=typer.colors.RED,
            )
            round_trip_ok = False
    if round_trip_ok:
        typer.secho("All sessions passed round-trip serialization/deserialization.", fg=typer.colors.GREEN)
    else:
        typer.secho("Some sessions failed round-trip serialization/deserialization.", fg=typer.colors.RED)

    if output_parquet:
        try:
            import pandas as pd

            df = pd.DataFrame([s.to_dict() for s in session_map.values()])
            df.to_parquet(output_parquet, index=False)
            typer.secho(f"Merged and deduplicated sessions exported to {output_parquet}", fg=typer.colors.GREEN)
        except ImportError:
            typer.secho("pandas is required for Parquet export. Please install pandas.", fg=typer.colors.RED)

    # Default output_json if not specified
    output_json_path = output_json or str(Path.cwd() / "merged_sessions.json")
    with open(output_json_path, "w") as f:
        json.dump([s.to_dict() for s in session_map.values()], f, indent=2, default=str)
    typer.secho(f"Merged and deduplicated sessions exported to {output_json_path}", fg=typer.colors.GREEN)

    # Always: Validate round-trip serialization of merged output
    with open(output_json_path, "r") as f:
        merged_data = json.load(f)
    errors = 0
    for i, s in enumerate(merged_data):
        try:
            TestSession.from_dict(s)
        except Exception as e:
            typer.secho(f"Round-trip validation failed for session {i}: {e}", fg=typer.colors.RED)
            errors += 1
    if errors == 0:
        typer.secho("All merged sessions passed round-trip serialization/deserialization.", fg=typer.colors.GREEN)
    else:
        typer.secho(f"{errors} session(s) failed round-trip validation.", fg=typer.colors.RED)
        raise typer.Exit(code=1)


@app.command()
def export_postgres(
    input_json: str = typer.Option(..., help="Path to merged JSON file"),
    db_url: str = typer.Option(..., help="Postgres connection string, e.g. postgresql://user:pass@host/dbname"),
    table_prefix: str = typer.Option("insight_", help="Prefix for table names (default: 'insight_')"),
):
    """
    Export merged TestSession JSON to a normalized PostgreSQL schema for BI tools like Metabase.
    """
    import json

    import psycopg2

    sessions_table = f"{table_prefix}sessions"
    rerun_groups_table = f"{table_prefix}rerun_groups"
    test_results_table = f"{table_prefix}test_results"

    conn = psycopg2.connect(db_url)
    cur = conn.cursor()

    with open(input_json, "r") as f:
        sessions = json.load(f)

    for session in sessions:
        # Insert session
        cur.execute(
            f"""
            INSERT INTO {sessions_table}
            (sut_name, session_id, session_start_time, session_stop_time, session_duration, session_tags, testing_system)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING id
            """,
            (
                session["sut_name"],
                session["session_id"],
                session["session_start_time"],
                session["session_stop_time"],
                session["session_duration"],
                json.dumps(session.get("session_tags", {})),
                json.dumps(session.get("testing_system", {})),
            ),
        )
        session_db_id = cur.fetchone()[0]

        # Insert rerun test groups
        group_db_ids = {}
        for group in session.get("rerun_test_groups", []):
            cur.execute(
                f"""
                INSERT INTO {rerun_groups_table} (session_id, nodeid)
                VALUES (%s, %s)
                RETURNING id
                """,
                (session_db_id, group["nodeid"]),
            )
            group_db_id = cur.fetchone()[0]
            group_db_ids[group["nodeid"]] = group_db_id

        # Insert test results
        for test in session.get("test_results", []):
            rerun_group_id = group_db_ids.get(test["nodeid"])
            cur.execute(
                f"""
                INSERT INTO {test_results_table}
                (session_id, rerun_group_id, nodeid, outcome, start_time, stop_time, duration,
                 caplog, capstderr, capstdout, longreprtext, has_warning)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    session_db_id,
                    rerun_group_id,
                    test["nodeid"],
                    test["outcome"],
                    test["start_time"],
                    test["stop_time"],
                    test["duration"],
                    test.get("caplog", ""),
                    test.get("capstderr", ""),
                    test.get("capstdout", ""),
                    test.get("longreprtext", ""),
                    test.get("has_warning", False),
                ),
            )

    conn.commit()
    cur.close()
    conn.close()
    typer.secho(
        f"Export to PostgreSQL completed successfully! Tables used: {sessions_table}, {rerun_groups_table}, {test_results_table}",
        fg=typer.colors.GREEN,
    )


@app.command()
def clear_postgres(
    db_url: str = typer.Option(..., help="Postgres connection string, e.g. postgresql://user:pass@host/dbname"),
):
    """
    Clear all data from test_results, rerun_test_groups, and test_sessions tables in the correct order.
    """
    import psycopg2

    conn = psycopg2.connect(db_url)
    cur = conn.cursor()
    cur.execute("TRUNCATE TABLE test_results, rerun_test_groups, test_sessions RESTART IDENTITY CASCADE;")
    conn.commit()
    cur.close()
    conn.close()
    typer.secho("All tables truncated and identities reset.", fg=typer.colors.GREEN)


if __name__ == "__main__":
    app()
