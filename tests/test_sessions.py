import json
import pytest
from pathlib import Path

from tbweightcalc.sessions import SessionStore


SAMPLE_LIFTS = [
    {"exercise": "zercher squat", "one_rm": 283, "body_weight": None, "bar_weight": 45.0, "bar_label": None},
    {"exercise": "bench press", "one_rm": 275, "body_weight": None, "bar_weight": 45.0, "bar_label": None},
    {"exercise": "deadlift", "one_rm": 342, "body_weight": None, "bar_weight": 45.0, "bar_label": "C-70"},
    {"exercise": "weighted pullup", "one_rm": 297, "body_weight": 212, "bar_weight": 45.0, "bar_label": None},
]


@pytest.fixture
def store(tmp_path):
    return SessionStore(path=tmp_path / "sessions.json")


# ---------------------------------------------------------------------------
# save_session
# ---------------------------------------------------------------------------

def test_save_creates_file(store, tmp_path):
    store.save_session("My Program", SAMPLE_LIFTS)
    assert (tmp_path / "sessions.json").exists()


def test_save_returns_session_dict(store):
    s = store.save_session("My Program", SAMPLE_LIFTS)
    assert s["name"] == "My Program"
    assert s["lifts"] == SAMPLE_LIFTS
    assert "id" in s
    assert "created" in s


def test_save_multiple_sessions(store):
    store.save_session("Block A", SAMPLE_LIFTS)
    store.save_session("Block B", SAMPLE_LIFTS[:2])
    sessions = store.list_sessions()
    assert len(sessions) == 2
    assert sessions[0]["name"] == "Block A"
    assert sessions[1]["name"] == "Block B"


def test_save_updates_existing_by_name(store):
    s1 = store.save_session("My Program", SAMPLE_LIFTS)
    orig_id = s1["id"]
    orig_created = s1["created"]

    new_lifts = SAMPLE_LIFTS[:2]
    s2 = store.save_session("My Program", new_lifts)

    assert s2["id"] == orig_id
    assert s2["created"] == orig_created
    assert "updated" in s2
    assert s2["lifts"] == new_lifts

    sessions = store.list_sessions()
    assert len(sessions) == 1


def test_save_name_match_case_insensitive(store):
    store.save_session("My Program", SAMPLE_LIFTS)
    store.save_session("MY PROGRAM", SAMPLE_LIFTS[:1])
    sessions = store.list_sessions()
    assert len(sessions) == 1
    assert sessions[0]["lifts"] == SAMPLE_LIFTS[:1]


# ---------------------------------------------------------------------------
# list_sessions
# ---------------------------------------------------------------------------

def test_list_sessions_empty(store):
    assert store.list_sessions() == []


def test_list_sessions_returns_all(store):
    store.save_session("A", SAMPLE_LIFTS)
    store.save_session("B", SAMPLE_LIFTS)
    sessions = store.list_sessions()
    assert len(sessions) == 2


# ---------------------------------------------------------------------------
# load_session
# ---------------------------------------------------------------------------

def test_load_by_exact_name(store):
    store.save_session("Home Block", SAMPLE_LIFTS)
    s = store.load_session("Home Block")
    assert s is not None
    assert s["name"] == "Home Block"


def test_load_by_name_case_insensitive(store):
    store.save_session("Home Block", SAMPLE_LIFTS)
    s = store.load_session("home block")
    assert s is not None


def test_load_by_partial_name(store):
    store.save_session("TB2026-02 Home", SAMPLE_LIFTS)
    s = store.load_session("TB2026")
    assert s is not None
    assert s["name"] == "TB2026-02 Home"


def test_load_by_id_prefix(store):
    saved = store.save_session("My Program", SAMPLE_LIFTS)
    s = store.load_session(saved["id"][:4])
    assert s is not None
    assert s["id"] == saved["id"]


def test_load_by_index(store):
    store.save_session("First", SAMPLE_LIFTS)
    store.save_session("Second", SAMPLE_LIFTS[:2])
    s = store.load_session("2")
    assert s is not None
    assert s["name"] == "Second"


def test_load_nonexistent_returns_none(store):
    store.save_session("My Program", SAMPLE_LIFTS)
    assert store.load_session("nothing") is None


def test_load_index_out_of_range_returns_none(store):
    store.save_session("My Program", SAMPLE_LIFTS)
    assert store.load_session("99") is None


# ---------------------------------------------------------------------------
# delete_session
# ---------------------------------------------------------------------------

def test_delete_by_name(store):
    store.save_session("My Program", SAMPLE_LIFTS)
    result = store.delete_session("My Program")
    assert result is True
    assert store.list_sessions() == []


def test_delete_by_index(store):
    store.save_session("A", SAMPLE_LIFTS)
    store.save_session("B", SAMPLE_LIFTS[:1])
    result = store.delete_session("1")
    assert result is True
    sessions = store.list_sessions()
    assert len(sessions) == 1
    assert sessions[0]["name"] == "B"


def test_delete_nonexistent_returns_false(store):
    result = store.delete_session("nothing")
    assert result is False


def test_delete_does_not_affect_others(store):
    store.save_session("Keep", SAMPLE_LIFTS)
    store.save_session("Remove", SAMPLE_LIFTS[:1])
    store.delete_session("Remove")
    sessions = store.list_sessions()
    assert len(sessions) == 1
    assert sessions[0]["name"] == "Keep"


# ---------------------------------------------------------------------------
# persistence (file round-trip)
# ---------------------------------------------------------------------------

def test_sessions_persist_across_instances(tmp_path):
    path = tmp_path / "sessions.json"
    store1 = SessionStore(path=path)
    store1.save_session("Persistent", SAMPLE_LIFTS)

    store2 = SessionStore(path=path)
    sessions = store2.list_sessions()
    assert len(sessions) == 1
    assert sessions[0]["name"] == "Persistent"
    assert sessions[0]["lifts"] == SAMPLE_LIFTS


def test_lifts_stored_correctly(store):
    store.save_session("Check Lifts", SAMPLE_LIFTS)
    s = store.load_session("Check Lifts")
    assert s["lifts"][0]["exercise"] == "zercher squat"
    assert s["lifts"][0]["one_rm"] == 283
    assert s["lifts"][3]["body_weight"] == 212


# ---------------------------------------------------------------------------
# CLI integration: --list-sessions, --load-session, --delete-session
# ---------------------------------------------------------------------------

def test_cli_list_sessions(tmp_path, capsys, monkeypatch):
    from tbweightcalc import cli

    path = tmp_path / "sessions.json"
    store = SessionStore(path=path)
    store.save_session("TB Home", SAMPLE_LIFTS)

    monkeypatch.setattr(cli, "SessionStore", lambda: store)

    import sys
    monkeypatch.setattr(sys, "argv", ["tbcalc", "--list-sessions"])
    cli.main()

    out = capsys.readouterr().out
    assert "TB Home" in out


def test_cli_delete_session(tmp_path, capsys, monkeypatch):
    from tbweightcalc import cli

    path = tmp_path / "sessions.json"
    store = SessionStore(path=path)
    store.save_session("TB Home", SAMPLE_LIFTS)

    monkeypatch.setattr(cli, "SessionStore", lambda: store)

    import sys
    monkeypatch.setattr(sys, "argv", ["tbcalc", "--delete-session", "TB Home"])
    cli.main()

    out = capsys.readouterr().out
    assert "Deleted" in out
    assert store.list_sessions() == []


def test_cli_delete_session_not_found(tmp_path, capsys, monkeypatch):
    from tbweightcalc import cli

    path = tmp_path / "sessions.json"
    store = SessionStore(path=path)

    monkeypatch.setattr(cli, "SessionStore", lambda: store)

    import sys
    monkeypatch.setattr(sys, "argv", ["tbcalc", "--delete-session", "nonexistent"])
    cli.main()

    out = capsys.readouterr().out
    assert "No session found" in out
