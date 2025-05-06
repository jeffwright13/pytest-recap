import json
from pathlib import Path
from typing import List, Optional

from filelock import FileLock


class JSONStorage:
    """
    Stores test sessions in a local JSON file, supporting both single-session (dict) and multi-session (list) modes.
    - Single-session mode (used by the pytest plugin): writes a single session as a dict, overwriting the file.
    - Multi-session/archive mode: appends sessions to a list, allowing for archival of multiple sessions in one file.
    - Thread/process-safe via file locking.

    Args:
        file_path (Optional[str]): Path to the JSON file. Defaults to ~/.pytest_recap/sessions.json

    Methods:
        save_session(session_data: dict, single: bool = False):
            Appends session_data to the file as a list (default), or overwrites as a dict if single=True.
        save_single_session(session_data: dict):
            Overwrites the file with a single session dict (for plugin recap output).
        load_sessions(lock: bool = True) -> List[dict]:
            Loads all sessions as a list (returns [] if file is a dict or empty).

    Example usage:
        storage = JSONStorage(file_path="sessions.json")
        storage.save_session(session_dict)  # archive mode
        storage.save_single_session(session_dict)  # single recap file
    """

    def __init__(self, file_path: Optional[str] = None):
        self.file_path = Path(file_path) if file_path else Path.home() / ".pytest_recap" / "sessions.json"
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        self.lock_path = f"{self.file_path}.lock"
        if not self.file_path.exists():
            # Only lock here if other processes could create at the same time
            with FileLock(self.lock_path):
                self._write_json([])

    def save_session(self, session_data: dict, single: bool = False) -> None:
        """
        Save a session. If single=True, write as a dict (overwrite file). If False (default), append to list (archive mode).
        In archive mode, always writes a list. If the file is a dict or empty, starts a new list.
        """
        with FileLock(self.lock_path):
            if single:
                self._write_json(session_data)
            else:
                # Always ensure archive file is a list
                try:
                    sessions = self.load_sessions(lock=False)
                    if not isinstance(sessions, list):
                        sessions = []
                except Exception:
                    sessions = []
                sessions.append(session_data)
                self._write_json(sessions)

    def save_single_session(self, session_data: dict) -> None:
        """
        Save a single session as a dict (overwrite file). For plugin recap output.
        """
        self.save_session(session_data, single=True)

    def load_sessions(self, lock: bool = True) -> List[dict]:
        if lock:
            with FileLock(self.lock_path):
                return self._load_sessions_unlocked()
        else:
            return self._load_sessions_unlocked()

    def _load_sessions_unlocked(self) -> List[dict]:
        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data if isinstance(data, list) else data.get("sessions", [])
        except (FileNotFoundError, json.JSONDecodeError):
            return []

    def _write_json(self, data) -> None:
        with open(self.file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
