from __future__ import annotations

import datetime
import json
import uuid
from pathlib import Path
from typing import Optional


_DEFAULT_SESSIONS_FILE = Path("~/.config/tbcalc/sessions.json").expanduser()


class SessionStore:
    """Persistent storage for saved lift sessions."""

    def __init__(self, path: Path = _DEFAULT_SESSIONS_FILE):
        self.path = path

    def _load(self) -> dict:
        if not self.path.exists():
            return {"sessions": []}
        with open(self.path) as f:
            return json.load(f)

    def _save(self, data: dict) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.path, "w") as f:
            json.dump(data, f, indent=2)

    def list_sessions(self) -> list[dict]:
        return self._load()["sessions"]

    def save_session(self, name: str, lifts: list[dict]) -> dict:
        """Save or update a session by name. Returns the saved session dict."""
        data = self._load()
        today = datetime.date.today().isoformat()

        for i, s in enumerate(data["sessions"]):
            if s["name"].lower() == name.lower():
                updated = {
                    "id": s["id"],
                    "name": s["name"],
                    "created": s["created"],
                    "updated": today,
                    "lifts": lifts,
                }
                data["sessions"][i] = updated
                self._save(data)
                return updated

        new_session = {
            "id": str(uuid.uuid4())[:8],
            "name": name,
            "created": today,
            "lifts": lifts,
        }
        data["sessions"].append(new_session)
        self._save(data)
        return new_session

    def load_session(self, name_or_id: str) -> Optional[dict]:
        """Find a session by exact name, partial name, 1-based index, or id prefix."""
        sessions = self.list_sessions()
        lower = name_or_id.lower()

        for s in sessions:
            if s["name"].lower() == lower:
                return s

        for s in sessions:
            if lower in s["name"].lower():
                return s

        try:
            idx = int(name_or_id)
            if 1 <= idx <= len(sessions):
                return sessions[idx - 1]
        except ValueError:
            pass

        for s in sessions:
            if s["id"].startswith(name_or_id):
                return s

        return None

    def delete_session(self, name_or_id: str) -> bool:
        """Delete a session. Returns True if found and deleted."""
        data = self._load()
        session = self.load_session(name_or_id)
        if session is None:
            return False
        data["sessions"] = [s for s in data["sessions"] if s["id"] != session["id"]]
        self._save(data)
        return True
