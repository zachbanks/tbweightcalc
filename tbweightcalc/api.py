"""
REST API interface for tbweightcalc.

Install the optional dependency group to use this:
    pip install tbweightcalc[api]

Run locally:
    uvicorn tbweightcalc.api:app --reload

All business logic lives in tbweightcalc.core; this module is purely the
HTTP transport layer.
"""
from __future__ import annotations

from typing import Optional

try:
    from fastapi import FastAPI, HTTPException
    from pydantic import BaseModel
except ImportError as e:
    raise ImportError(
        "FastAPI is required to use the tbweightcalc API. "
        "Install it with: pip install tbweightcalc[api]"
    ) from e

from tbweightcalc.core import (
    build_program_markdown,
    _apply_lift_adjustment,
    parse_one_rm_string,
)
from tbweightcalc.sessions import SessionStore

app = FastAPI(
    title="tbweightcalc API",
    description="Tactical Barbell Max Strength calculator",
    version="1.0.0",
)

_store = SessionStore()


# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------

class LiftIn(BaseModel):
    exercise: str
    one_rm: int
    body_weight: Optional[int] = None
    bar_weight: float = 45.0
    bar_label: Optional[str] = None


class ProgramRequest(BaseModel):
    lifts: list[LiftIn]
    week: str = "all"   # "1"–"6" or "all"


class ProgramResponse(BaseModel):
    markdown: str


class AdjustRequest(BaseModel):
    lifts: list[LiftIn]
    pct: float
    exercise: Optional[str] = None


class SessionIn(BaseModel):
    name: str
    lifts: list[LiftIn]


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/", summary="Health check")
def health() -> dict:
    return {"status": "ok", "service": "tbweightcalc"}


@app.post("/calculate", response_model=ProgramResponse, summary="Generate program markdown")
def calculate(req: ProgramRequest) -> ProgramResponse:
    """
    Generate the Tactical Barbell program for the given lifts and week.

    - **lifts**: list of lift objects (exercise, one_rm, optionally body_weight / bar_weight)
    - **week**: "1"–"6" for a single week, or "all" for the complete 6-week block
    """
    lifts = [l.model_dump() for l in req.lifts]
    markdown = build_program_markdown(lifts, week=req.week, for_pdf=False)
    return ProgramResponse(markdown=markdown)


@app.post("/adjust", summary="Apply % adjustment to lifts")
def adjust(req: AdjustRequest) -> dict:
    """Apply a percentage adjustment to one_rm values and return updated lifts."""
    lifts = [l.model_dump() for l in req.lifts]
    updated = _apply_lift_adjustment(lifts, req.pct, req.exercise)
    return {"lifts": updated}


@app.get("/sessions", summary="List saved sessions")
def list_sessions() -> dict:
    return {"sessions": _store.list_sessions()}


@app.get("/sessions/{name}", summary="Load a session by name, number, or id")
def get_session(name: str) -> dict:
    session = _store.load_session(name)
    if session is None:
        raise HTTPException(status_code=404, detail=f"Session '{name}' not found")
    return session


@app.post("/sessions", summary="Save or update a session")
def save_session(req: SessionIn) -> dict:
    lifts = [l.model_dump() for l in req.lifts]
    session = _store.save_session(req.name, lifts)
    return session


@app.delete("/sessions/{name}", summary="Delete a session")
def delete_session(name: str) -> dict:
    if not _store.delete_session(name):
        raise HTTPException(status_code=404, detail=f"Session '{name}' not found")
    return {"deleted": name}
