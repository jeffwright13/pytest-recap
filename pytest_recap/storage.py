import json
from pathlib import Path
from typing import List, Optional
from filelock import FileLock

class JSONStorage:
    """Stores test sessions as a list of dicts in a local JSON file, with file locking for concurrency."""
    def __init__(self, file_path: Optional[str] = None):
        self.file_path = Path(file_path) if file_path else Path.home() / ".pytest_recap" / "sessions.json"
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        self.lock_path = f"{self.file_path}.lock"
        if not self.file_path.exists():
            # Only lock here if other processes could create at the same time
            with FileLock(self.lock_path):
                self._write_json([])

    def save_session(self, session_data: dict) -> None:
        with FileLock(self.lock_path):
            sessions = self.load_sessions(lock=False)
            sessions.append(session_data)
            self._write_json(sessions)

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

    def _write_json(self, sessions: List[dict]) -> None:
        with open(self.file_path, "w", encoding="utf-8") as f:
            json.dump(sessions, f, indent=2)
