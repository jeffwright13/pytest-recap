import json
import os
import threading
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
        self._thread_lock = threading.RLock()
        if not self.file_path.exists():
            # Only lock here if other processes could create at the same time
            with FileLock(self.lock_path):
                self._write_json([])

    def save_session(self, session_data: dict, single: bool = False, indent=2) -> None:
        """
        Save a session. If single=True, write as a dict (overwrite file). If False (default), append to list (archive mode).
        In archive mode, always writes a list. If the file is a dict or empty, starts a new list.
        Propagates PermissionError if file is not writable.
        """
        with self._thread_lock:
            with FileLock(self.lock_path):
                if single:
                    self._write_json(session_data, indent=indent)
                else:
                    try:
                        sessions = self.load_sessions(lock=False)
                        if not isinstance(sessions, list):
                            sessions = []
                    except Exception:
                        sessions = []
                    sessions.append(session_data)
                    self._write_json(sessions, indent=indent)
            # Only clean up lock files if the above succeeded
            self._cleanup_zero_byte_lock_files()

    def save_single_session(self, session_data: dict, indent=2) -> None:
        """
        Save a single session as a dict (overwrite file). For plugin recap output.
        """
        with self._thread_lock:
            self.save_session(session_data, single=True, indent=indent)
            self._cleanup_zero_byte_lock_files()

    def load_sessions(self, lock: bool = True) -> List[dict]:
        with self._thread_lock:
            if lock:
                with FileLock(self.lock_path):
                    return self._load_sessions_unlocked()
            else:
                return self._load_sessions_unlocked()

    def _load_sessions_unlocked(self) -> List[dict]:
        """
        Load sessions from the JSON file. Returns a list of sessions, or [] if file missing/corrupt.
        Uses filelock for safety in load_sessions().
        """
        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            # Accept both list and dict (legacy), but always return a list
            if isinstance(data, list):
                return data
            elif isinstance(data, dict):
                # Only accept dicts with a 'sessions' key containing a list
                if "sessions" in data and isinstance(data["sessions"], list):
                    return data["sessions"]
                else:
                    return []
            else:
                return []
        except (FileNotFoundError, json.JSONDecodeError):
            return []

    def _write_json(self, data, indent=2) -> None:
        """
        Atomically write JSON data to self.file_path using a temp file and os.replace for durability and crash-safety.
        Raises PermissionError if the file is not writable.
        """
        tmp_path = self.file_path.with_suffix(".tmp")
        try:
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=indent)
                f.flush()
                os.fsync(f.fileno())
            os.replace(str(tmp_path), str(self.file_path))
        except PermissionError:
            # Explicitly propagate PermissionError for test expectations
            raise

    def _cleanup_zero_byte_lock_files(self):
        """
        Delete all 0-byte .lock files in the session directory. This prevents accumulation of orphaned lock files.
        Only 0-byte files are deleted; non-empty lock files are left untouched for safety.
        """
        session_dir = self.file_path.parent
        for fname in os.listdir(session_dir):
            if fname.endswith(".lock"):
                fpath = session_dir / fname
                try:
                    if os.path.isfile(fpath) and os.path.getsize(fpath) == 0:
                        os.remove(fpath)
                except Exception:
                    pass  # Ignore errors during cleanup
