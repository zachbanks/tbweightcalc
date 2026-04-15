"""Textual TUI for Tactical Barbell Max Strength Calculator."""
from __future__ import annotations

import argparse
import datetime
from dataclasses import dataclass, field
from typing import Optional

from textual import on
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical, ScrollableContainer
from textual.screen import Screen, ModalScreen
from textual.widgets import (
    Button,
    DataTable,
    Footer,
    Header,
    Input,
    Label,
    ListItem,
    ListView,
    RadioButton,
    RadioSet,
    Rule,
    Static,
    TextArea,
)

from tbweightcalc.sessions import SessionStore
from tbweightcalc.cli import (
    _apply_lift_adjustment,
    _ADJUSTMENT_PRESETS,
    build_program_markdown,
    copy_to_clipboard,
    default_pdf_path,
    format_exercise_name,
    markdown_to_pdf,
    parse_one_rm_string,
    parse_weighted_pullup_string,
    INTERACTIVE_LIFT_SLOTS,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

TEMPLATES = {
    "1": {"label": "Classic", "exercises": ["squat", "bench press", "deadlift"]},
    "2": {"label": "Front-Squat Block", "exercises": ["front squat", "overhead press", "deadlift"]},
    "3": {"label": "Zercher Block", "exercises": ["zercher squat", "bench press", "deadlift"]},
    "4": {"label": "Custom", "exercises": []},
}

CSS = """
Screen {
    background: $surface;
}

.screen-title {
    text-style: bold;
    color: $accent;
    margin: 0 0 1 0;
    padding: 0 1;
}

.section-label {
    color: $text-muted;
    margin: 1 0 0 0;
    padding: 0 1;
}

.card {
    border: round $accent;
    padding: 1 2;
    margin: 0 1 1 1;
}

.btn-row {
    height: 3;
    margin: 1 1 0 1;
    align: right middle;
}

.btn-row Button {
    margin-left: 1;
}

.btn-primary {
    background: $accent;
}

.lift-row {
    height: 3;
    margin: 0 1;
}

.lift-label {
    width: 18;
    content-align: left middle;
    padding: 0 1;
}

.lift-input {
    width: 16;
}

.bar-input {
    width: 8;
}

.label-input {
    width: 14;
}

#session-list {
    height: 1fr;
    border: round $panel;
    margin: 0 1;
}

#output-area {
    height: 1fr;
    border: round $panel;
    margin: 0 1;
}

.warning {
    color: $warning;
    margin: 0 1;
}

.success {
    color: $success;
    margin: 0 1;
}

RadioSet {
    margin: 0 1;
}

.slot-label {
    text-style: bold;
    color: $text;
    margin: 1 0 0 1;
    padding: 0 1;
}

.slot-options {
    margin: 0 2;
}
"""

# ---------------------------------------------------------------------------
# Shared state
# ---------------------------------------------------------------------------

@dataclass
class AppState:
    store: SessionStore = field(default_factory=SessionStore)
    lifts: list[dict] = field(default_factory=list)
    title: str = ""
    week: str = "all"
    out_mode: str = "b"
    loaded_session_name: Optional[str] = None
    mode: str = "new"          # "new" | "edit" | "duplicate" | "output"
    template: str = "1"
    skip_save: bool = False


# ---------------------------------------------------------------------------
# Screens
# ---------------------------------------------------------------------------

class HomeScreen(Screen):
    """Session list — entry point of the app."""

    BINDINGS = [
        Binding("n", "new_program", "New"),
        Binding("l", "load_selected", "Load"),
        Binding("enter", "load_selected", "Open", show=False),
        Binding("delete", "delete_selected", "Delete", show=False),
        Binding("d", "delete_selected", "Delete"),
    ]

    def compose(self) -> ComposeResult:
        yield Header(show_clock=False)
        yield Static("Tactical Barbell Max Strength", classes="screen-title")
        yield Rule()
        yield Static("Saved Sessions", classes="section-label")
        yield ListView(id="session-list")
        yield Rule()
        with Horizontal(classes="btn-row"):
            yield Button("New [n]", id="btn-new", variant="primary")
            yield Button("Load [l]", id="btn-load", variant="default")
            yield Button("Delete [d]", id="btn-delete", variant="error")
        yield Footer()

    def on_mount(self) -> None:
        self._refresh_list()

    def _refresh_list(self) -> None:
        lv = self.query_one("#session-list", ListView)
        lv.clear()
        sessions = self.app.state.store.list_sessions()
        if not sessions:
            lv.append(ListItem(Label("  (no saved sessions — press N to start)")))
        else:
            for i, s in enumerate(sessions, 1):
                date = s.get("updated") or s["created"]
                lv.append(ListItem(Label(f"  [{i}]  {s['name']}  ({date})  id:{s['id']}")))

    def _selected_index(self) -> int | None:
        lv = self.query_one("#session-list", ListView)
        if lv.index is None:
            return None
        sessions = self.app.state.store.list_sessions()
        if not sessions:
            return None
        return lv.index  # 0-based

    @on(Button.Pressed, "#btn-new")
    def action_new_program(self) -> None:
        state = self.app.state
        state.lifts = []
        state.loaded_session_name = None
        state.mode = "new"
        state.skip_save = False
        self.app.push_screen(SetupScreen())

    @on(Button.Pressed, "#btn-load")
    def action_load_selected(self) -> None:
        idx = self._selected_index()
        if idx is None:
            self.notify("Select a session first.", severity="warning")
            return
        sessions = self.app.state.store.list_sessions()
        session = sessions[idx]
        state = self.app.state
        state.lifts = [dict(l) for l in session["lifts"]]
        state.loaded_session_name = session["name"]
        self.app.push_screen(ActionScreen())

    @on(Button.Pressed, "#btn-delete")
    def action_delete_selected(self) -> None:
        idx = self._selected_index()
        if idx is None:
            self.notify("Select a session to delete.", severity="warning")
            return
        sessions = self.app.state.store.list_sessions()
        session = sessions[idx]
        self.app.state.store.delete_session(session["id"])
        self.notify(f"Deleted '{session['name']}'.", severity="information")
        self._refresh_list()


class ActionScreen(Screen):
    """Choose what to do with a loaded session: output / edit / duplicate."""

    BINDINGS = [
        Binding("escape", "app.pop_screen", "Back"),
        Binding("o", "quick_output", "Output"),
        Binding("e", "quick_edit", "Edit"),
        Binding("d", "quick_duplicate", "Duplicate"),
        Binding("ctrl+enter", "go_continue", "Continue"),
    ]

    def compose(self) -> ComposeResult:
        state = self.app.state
        yield Header(show_clock=False)
        yield Static(f"Loaded: {state.loaded_session_name}", classes="screen-title")
        yield Rule()
        yield Static("Press o / e / d to jump straight to that action.", classes="section-label")
        with Container(classes="card"):
            with RadioSet(id="action-radio"):
                yield RadioButton("Output program directly", id="r-output", value=True)
                yield RadioButton("Edit and save", id="r-edit")
                yield RadioButton("Duplicate with modifications", id="r-duplicate")
        with Horizontal(classes="btn-row"):
            yield Button("Back", id="btn-back", variant="default")
            yield Button("Continue [ctrl+↵]", id="btn-continue", variant="primary")
        yield Footer()

    @on(Button.Pressed, "#btn-back")
    def go_back(self) -> None:
        self.app.pop_screen()

    def action_quick_output(self) -> None:
        self.query_one("#r-output", RadioButton).value = True
        self._do_continue("r-output")

    def action_quick_edit(self) -> None:
        self.query_one("#r-edit", RadioButton).value = True
        self._do_continue("r-edit")

    def action_quick_duplicate(self) -> None:
        self.query_one("#r-duplicate", RadioButton).value = True
        self._do_continue("r-duplicate")

    def action_go_continue(self) -> None:
        rs = self.query_one("#action-radio", RadioSet)
        pressed = rs.pressed_button
        bid = pressed.id if pressed else "r-output"
        self._do_continue(bid)

    @on(Button.Pressed, "#btn-continue")
    def go_continue(self) -> None:
        self.action_go_continue()

    def _do_continue(self, bid: str) -> None:
        state = self.app.state
        if bid == "r-output":
            state.mode = "output"
            state.title = state.loaded_session_name or ""
            state.skip_save = True
            self.app.push_screen(GenerateScreen())
        elif bid == "r-edit":
            state.mode = "edit"
            state.skip_save = False
            self.app.push_screen(SetupScreen(title_only=True))
        else:
            state.mode = "duplicate"
            state.skip_save = False
            self.app.push_screen(SetupScreen(title_only=True, duplicate=True))


class SetupScreen(Screen):
    """Enter program title and choose template."""

    BINDINGS = [
        Binding("escape", "app.pop_screen", "Back"),
        Binding("ctrl+enter", "go_next", "Next"),
    ]

    def __init__(self, title_only: bool = False, duplicate: bool = False):
        super().__init__()
        self._title_only = title_only      # edit/dup: skip template
        self._duplicate = duplicate

    def compose(self) -> ComposeResult:
        state = self.app.state
        yield Header(show_clock=False)
        yield Static("Program Setup", classes="screen-title")
        yield Rule()

        # Default title
        if state.mode == "duplicate":
            default_title = f"Copy of {state.loaded_session_name}"
        elif state.loaded_session_name:
            default_title = state.loaded_session_name
        else:
            default_title = f"Tactical Barbell Max Strength: {datetime.date.today():%Y-%m-%d}"

        yield Static("Program Title", classes="section-label")
        with Container(classes="card"):
            yield Input(value=default_title, id="title-input", placeholder="Program title")

        if not self._title_only:
            yield Static("Template", classes="section-label")
            with Container(classes="card"):
                with RadioSet(id="template-radio"):
                    yield RadioButton("Classic  (Squat / Bench / Deadlift / WPU)", id="t1", value=True)
                    yield RadioButton("Front-Squat Block  (Front Squat / OHP / Deadlift / WPU)", id="t2")
                    yield RadioButton("Zercher Block  (Zercher Squat / Bench / Deadlift / WPU)", id="t3")
                    yield RadioButton("Custom  (choose lifts manually)", id="t4")

        with Horizontal(classes="btn-row"):
            yield Button("Back", id="btn-back", variant="default")
            yield Button("Next [ctrl+↵]", id="btn-next", variant="primary")
        yield Footer()

    @on(Button.Pressed, "#btn-back")
    def go_back(self) -> None:
        self.app.pop_screen()

    @on(Button.Pressed, "#btn-next")
    def action_go_next(self) -> None:
        state = self.app.state
        state.title = self.query_one("#title-input", Input).value.strip()
        if not state.title:
            state.title = f"Tactical Barbell Max Strength: {datetime.date.today():%Y-%m-%d}"

        if self._title_only:
            # edit / duplicate: skip template, go straight to adjustment (dup) or review (edit)
            if self._duplicate:
                self.app.push_screen(AdjustmentScreen())
            else:
                self.app.push_screen(ReviewScreen())
            return

        # Pick template
        rs = self.query_one("#template-radio", RadioSet)
        pressed = rs.pressed_button
        template_id = "t1"
        if pressed:
            template_id = pressed.id or "t1"
        state.template = template_id[-1]   # "1" / "2" / "3" / "4"

        if state.template == "4":
            self.app.push_screen(CustomLiftScreen())
        else:
            self.app.push_screen(LiftEntryScreen())


class LiftEntryScreen(Screen):
    """Enter 1RM for each lift in the chosen preset template."""

    BINDINGS = [
        Binding("escape", "app.pop_screen", "Back"),
        Binding("ctrl+enter", "go_next", "Next"),
    ]

    def __init__(self) -> None:
        super().__init__()
        state_template = None  # resolved at compose time

    def compose(self) -> ComposeResult:
        state = self.app.state
        exercises = TEMPLATES[state.template]["exercises"]
        template_label = TEMPLATES[state.template]["label"]

        yield Header(show_clock=False)
        yield Static(f"Lift Data — {template_label}", classes="screen-title")
        yield Rule()
        yield Static("Enter 1RM or a set (e.g. '455' or '240 5').  Leave blank to skip.", classes="section-label")

        with ScrollableContainer():
            for ex in exercises:
                yield Static(format_exercise_name(ex), classes="slot-label")
                with Horizontal(classes="lift-row"):
                    yield Label("1RM / set:", classes="lift-label")
                    yield Input(id=f"orm_{ex.replace(' ','_')}", placeholder="e.g. 455 or 240 5", classes="lift-input")
                    yield Label("Bar (lb):", classes="lift-label")
                    yield Input(id=f"bar_{ex.replace(' ','_')}", value="45", classes="bar-input")
                    yield Label("Bar label:", classes="lift-label")
                    yield Input(id=f"lbl_{ex.replace(' ','_')}", placeholder="e.g. SSB", classes="label-input")

            yield Rule()
            yield Static("Weighted Pull-Up  (optional)", classes="slot-label")
            with Horizontal(classes="lift-row"):
                yield Label("Bodyweight (lb):", classes="lift-label")
                yield Input(id="wpu_bw", placeholder="e.g. 212", classes="lift-input")
                yield Label("WPU set:", classes="lift-label")
                yield Input(id="wpu_set", placeholder="e.g. 45 4 or bw 4", classes="lift-input")

        with Horizontal(classes="btn-row"):
            yield Button("Back", id="btn-back", variant="default")
            yield Button("Next [ctrl+↵]", id="btn-next", variant="primary")
        yield Footer()

    def _val(self, widget_id: str) -> str:
        try:
            return self.query_one(f"#{widget_id}", Input).value.strip()
        except Exception:
            return ""

    @on(Button.Pressed, "#btn-back")
    def go_back(self) -> None:
        self.app.pop_screen()

    @on(Button.Pressed, "#btn-next")
    def action_go_next(self) -> None:
        state = self.app.state
        exercises = TEMPLATES[state.template]["exercises"]
        lifts: list[dict] = []

        for ex in exercises:
            key = ex.replace(" ", "_")
            orm_raw = self._val(f"orm_{key}")
            if not orm_raw:
                continue
            one_rm = parse_one_rm_string(orm_raw)
            if one_rm is None:
                self.notify(f"Invalid 1RM for {format_exercise_name(ex)}: '{orm_raw}'", severity="error")
                return
            try:
                bar_weight = float(self._val(f"bar_{key}") or "45")
            except ValueError:
                bar_weight = 45.0
            bar_label = self._val(f"lbl_{key}") or None
            lifts.append({
                "exercise": ex,
                "one_rm": one_rm,
                "body_weight": None,
                "bar_weight": bar_weight,
                "bar_label": bar_label,
            })

        # WPU
        bw_raw = self._val("wpu_bw")
        wpu_raw = self._val("wpu_set")
        if bw_raw:
            try:
                bw = int(bw_raw)
                if wpu_raw:
                    est = parse_weighted_pullup_string(bw, wpu_raw)
                    if est is None:
                        self.notify("Could not parse WPU set — try '45 4' or 'bw 4'.", severity="error")
                        return
                    lifts.append({
                        "exercise": "weighted pullup",
                        "one_rm": est,
                        "body_weight": bw,
                        "bar_weight": 45.0,
                        "bar_label": None,
                    })
            except ValueError:
                self.notify("Invalid bodyweight value.", severity="error")
                return

        if not lifts:
            self.notify("Enter at least one lift.", severity="warning")
            return

        state.lifts = lifts
        self.app.push_screen(ReviewScreen())


class CustomLiftScreen(Screen):
    """Template 4: slot-based custom exercise selection."""

    BINDINGS = [
        Binding("escape", "app.pop_screen", "Back"),
        Binding("ctrl+enter", "go_next", "Next"),
    ]

    def compose(self) -> ComposeResult:
        yield Header(show_clock=False)
        yield Static("Custom Program — Select Lifts", classes="screen-title")
        yield Rule()
        yield Static("Choose one option per slot (or skip).", classes="section-label")

        with ScrollableContainer():
            for slot in INTERACTIVE_LIFT_SLOTS:
                yield Static(slot["name"], classes="slot-label")
                with RadioSet(id=f"slot_{INTERACTIVE_LIFT_SLOTS.index(slot)}"):
                    yield RadioButton("Skip this slot", id=f"slot_{INTERACTIVE_LIFT_SLOTS.index(slot)}_skip", value=True)
                    for opt in slot["options"]:
                        key = opt["exercise_name"].replace(" ", "_")
                        yield RadioButton(format_exercise_name(opt["exercise_name"]), id=f"slot_{INTERACTIVE_LIFT_SLOTS.index(slot)}_{key}")

                slot_idx = INTERACTIVE_LIFT_SLOTS.index(slot)
                ex_key = slot["options"][0]["exercise_name"].replace(" ", "_") if slot["options"] else "ex"
                yield Static("1RM / set:", classes="section-label")
                with Horizontal(classes="lift-row"):
                    yield Input(id=f"orm_slot{slot_idx}", placeholder="e.g. 455 or 240 5", classes="lift-input")
                    yield Label("Bar (lb):", classes="lift-label")
                    yield Input(id=f"bar_slot{slot_idx}", value="45", classes="bar-input")

            yield Rule()
            yield Static("Weighted Pull-Up  (optional)", classes="slot-label")
            with Horizontal(classes="lift-row"):
                yield Label("Bodyweight (lb):", classes="lift-label")
                yield Input(id="wpu_bw", placeholder="e.g. 212", classes="lift-input")
                yield Label("WPU set:", classes="lift-label")
                yield Input(id="wpu_set", placeholder="e.g. 45 4 or bw 4", classes="lift-input")

        with Horizontal(classes="btn-row"):
            yield Button("Back", id="btn-back", variant="default")
            yield Button("Next [ctrl+↵]", id="btn-next", variant="primary")
        yield Footer()

    def _val(self, widget_id: str) -> str:
        try:
            return self.query_one(f"#{widget_id}", Input).value.strip()
        except Exception:
            return ""

    @on(Button.Pressed, "#btn-back")
    def go_back(self) -> None:
        self.app.pop_screen()

    @on(Button.Pressed, "#btn-next")
    def action_go_next(self) -> None:
        state = self.app.state
        lifts: list[dict] = []

        for slot_idx, slot in enumerate(INTERACTIVE_LIFT_SLOTS):
            rs_id = f"slot_{slot_idx}"
            try:
                rs = self.query_one(f"#{rs_id}", RadioSet)
                pressed = rs.pressed_button
            except Exception:
                continue
            if pressed is None or pressed.id == f"{rs_id}_skip":
                continue

            # Find which exercise was selected
            ex_name = None
            for opt in slot["options"]:
                key = opt["exercise_name"].replace(" ", "_")
                if pressed.id == f"{rs_id}_{key}":
                    ex_name = opt["exercise_name"]
                    break
            if ex_name is None:
                continue

            orm_raw = self._val(f"orm_slot{slot_idx}")
            if not orm_raw:
                continue
            one_rm = parse_one_rm_string(orm_raw)
            if one_rm is None:
                self.notify(f"Invalid 1RM for {format_exercise_name(ex_name)}: '{orm_raw}'", severity="error")
                return
            try:
                bar_weight = float(self._val(f"bar_slot{slot_idx}") or "45")
            except ValueError:
                bar_weight = 45.0

            lifts.append({
                "exercise": ex_name,
                "one_rm": one_rm,
                "body_weight": None,
                "bar_weight": bar_weight,
                "bar_label": None,
            })

        # WPU
        bw_raw = self._val("wpu_bw")
        wpu_raw = self._val("wpu_set")
        if bw_raw and wpu_raw:
            try:
                bw = int(bw_raw)
                est = parse_weighted_pullup_string(bw, wpu_raw)
                if est is not None:
                    lifts.append({"exercise": "weighted pullup", "one_rm": est,
                                  "body_weight": bw, "bar_weight": 45.0, "bar_label": None})
            except ValueError:
                pass

        if not lifts:
            self.notify("Enter at least one lift.", severity="warning")
            return

        state.lifts = lifts
        self.app.push_screen(ReviewScreen())


class AdjustmentScreen(Screen):
    """Choose a % adjustment for duplicate mode (applied before review)."""

    BINDINGS = [
        Binding("escape", "app.pop_screen", "Back"),
        Binding("ctrl+enter", "go_next", "Next"),
    ]

    def compose(self) -> ComposeResult:
        state = self.app.state
        yield Header(show_clock=False)
        yield Static("Adjust 1RMs  (Duplicate)", classes="screen-title")
        yield Rule()

        exercise_names = [l["exercise"] for l in state.lifts]

        yield Static("Preset adjustment (applied to all 1RMs):", classes="section-label")
        with Container(classes="card"):
            with RadioSet(id="preset-radio"):
                yield RadioButton("Skip — no adjustment", id="p-skip", value=True)
                for i, (label, _) in enumerate(_ADJUSTMENT_PRESETS):
                    yield RadioButton(label, id=f"p-{i}")
                yield RadioButton("Custom %", id="p-custom")
            yield Input(id="custom-pct", placeholder="e.g. 7.5 or -3", classes="lift-input")

        yield Static("Apply to:", classes="section-label")
        with Container(classes="card"):
            with RadioSet(id="scope-radio"):
                yield RadioButton("All lifts", id="scope-all", value=True)
                for ex in exercise_names:
                    yield RadioButton(format_exercise_name(ex), id=f"scope-{ex.replace(' ','_')}")

        with Horizontal(classes="btn-row"):
            yield Button("Back", id="btn-back", variant="default")
            yield Button("Next [ctrl+↵]", id="btn-next", variant="primary")
        yield Footer()

    @on(Button.Pressed, "#btn-back")
    def go_back(self) -> None:
        self.app.pop_screen()

    @on(Button.Pressed, "#btn-next")
    def action_go_next(self) -> None:
        state = self.app.state
        rs = self.query_one("#preset-radio", RadioSet)
        pressed = rs.pressed_button
        pid = pressed.id if pressed else "p-skip"

        pct: float | None = None
        if pid == "p-skip":
            pct = None
        elif pid == "p-custom":
            raw = self.query_one("#custom-pct", Input).value.strip()
            try:
                pct = float(raw)
            except ValueError:
                self.notify("Invalid custom percentage.", severity="error")
                return
        else:
            try:
                idx = int(pid.split("-")[1])
                pct = _ADJUSTMENT_PRESETS[idx][1]
            except (ValueError, IndexError):
                pct = None

        if pct is not None:
            # Scope
            scope_rs = self.query_one("#scope-radio", RadioSet)
            scope_pressed = scope_rs.pressed_button
            exercise: str | None = None
            if scope_pressed and scope_pressed.id != "scope-all":
                # Reverse the ID mangling
                exercise_key = scope_pressed.id.replace("scope-", "").replace("_", " ")
                for l in state.lifts:
                    if l["exercise"].replace(" ", "_") == scope_pressed.id.replace("scope-", ""):
                        exercise = l["exercise"]
                        break
            state.lifts = _apply_lift_adjustment(state.lifts, pct, exercise)
            target = f"'{exercise}'" if exercise else "all lifts"
            self.notify(f"Applied {pct:+.4g}% to {target}.")

        self.app.push_screen(ReviewScreen())


class EditLiftModal(ModalScreen):
    """Modal to edit a single lift's 1RM in the review screen."""

    BINDINGS = [Binding("escape", "dismiss_modal", "Cancel", show=False)]

    def action_dismiss_modal(self) -> None:
        self.dismiss(False)

    def __init__(self, lift_idx: int):
        super().__init__()
        self._idx = lift_idx

    def compose(self) -> ComposeResult:
        state = self.app.state
        lift = state.lifts[self._idx]
        ex = lift["exercise"]
        is_wpu = lift.get("body_weight") is not None

        with Container(classes="card"):
            yield Static(f"Edit: {format_exercise_name(ex)}", classes="screen-title")
            yield Rule()
            if is_wpu:
                bw = lift.get("body_weight", "")
                added = lift["one_rm"] - (lift.get("body_weight") or 0)
                yield Label("Bodyweight (lb):")
                yield Input(value=str(bw), id="edit-bw")
                yield Label("Added weight (lb) at 1RM intensity:")
                yield Input(value=str(added), id="edit-added")
            else:
                yield Label("1RM or set (e.g. '455' or '240 5'):")
                yield Input(value=str(lift["one_rm"]), id="edit-orm")
                yield Label("Bar weight (lb):")
                yield Input(value=str(lift.get("bar_weight", 45)), id="edit-bar")
                yield Label("Bar label (optional):")
                yield Input(value=lift.get("bar_label") or "", id="edit-label")
            with Horizontal(classes="btn-row"):
                yield Button("Cancel", id="btn-cancel", variant="default")
                yield Button("Save", id="btn-save", variant="primary")

    def _val(self, wid: str) -> str:
        try:
            return self.query_one(f"#{wid}", Input).value.strip()
        except Exception:
            return ""

    @on(Button.Pressed, "#btn-cancel")
    def cancel(self) -> None:
        self.dismiss(False)

    @on(Button.Pressed, "#btn-save")
    def save(self) -> None:
        state = self.app.state
        lift = state.lifts[self._idx]
        is_wpu = lift.get("body_weight") is not None

        if is_wpu:
            try:
                bw = int(self._val("edit-bw"))
                added = int(self._val("edit-added"))
                lift["body_weight"] = bw
                lift["one_rm"] = bw + added
            except ValueError:
                self.app.notify("Invalid values.", severity="error")
                return
        else:
            orm_raw = self._val("edit-orm")
            one_rm = parse_one_rm_string(orm_raw)
            if one_rm is None:
                self.app.notify(f"Invalid 1RM: '{orm_raw}'", severity="error")
                return
            try:
                bar_weight = float(self._val("edit-bar") or "45")
            except ValueError:
                bar_weight = 45.0
            lift["one_rm"] = one_rm
            lift["bar_weight"] = bar_weight
            lift["bar_label"] = self._val("edit-label") or None

        state.lifts[self._idx] = lift
        self.dismiss(True)


class ReviewScreen(Screen):
    """Review all entered lifts; click a row to edit."""

    BINDINGS = [
        Binding("escape", "app.pop_screen", "Back"),
        Binding("e", "edit_selected", "Edit row"),
        Binding("ctrl+enter", "go_continue", "Continue"),
    ]

    def compose(self) -> ComposeResult:
        yield Header(show_clock=False)
        yield Static("Review Lifts", classes="screen-title")
        yield Rule()
        yield Static("Select row + [e] to edit  •  [ctrl+↵] to continue.", classes="section-label")
        yield DataTable(id="lift-table", cursor_type="row")
        with Horizontal(classes="btn-row"):
            yield Button("Back", id="btn-back", variant="default")
            yield Button("Edit [e]", id="btn-edit", variant="default")
            yield Button("Continue [ctrl+↵]", id="btn-continue", variant="primary")
        yield Footer()

    def on_mount(self) -> None:
        self._build_table()

    def _build_table(self) -> None:
        table = self.query_one("#lift-table", DataTable)
        table.clear(columns=True)
        table.add_columns("Exercise", "1RM", "Bar", "Body Weight")
        for lift in self.app.state.lifts:
            ex = format_exercise_name(lift["exercise"])
            orm = f"{lift['one_rm']}#"
            bw = lift.get("body_weight")
            bar_lbl = lift.get("bar_label") or ""
            bar_str = f"{lift.get('bar_weight', 45):.0f}#" + (f" ({bar_lbl})" if bar_lbl else "")
            bw_str = f"{bw}#" if bw is not None else "—"
            table.add_row(ex, orm, bar_str, bw_str)

    @on(Button.Pressed, "#btn-back")
    def go_back(self) -> None:
        self.app.pop_screen()

    @on(Button.Pressed, "#btn-edit")
    def action_edit_selected(self) -> None:
        table = self.query_one("#lift-table", DataTable)
        row = table.cursor_row
        if row < 0 or row >= len(self.app.state.lifts):
            self.notify("Select a lift row to edit.", severity="warning")
            return
        self._open_edit(row)

    @on(DataTable.RowSelected)
    def row_selected(self, event: DataTable.RowSelected) -> None:
        self._open_edit(event.cursor_row)

    def _open_edit(self, row: int) -> None:
        def on_close(saved: bool) -> None:
            if saved:
                self._build_table()
                self.notify("Lift updated.")
        self.app.push_screen(EditLiftModal(row), on_close)

    @on(Button.Pressed, "#btn-continue")
    def action_go_continue(self) -> None:
        self.app.push_screen(GenerateScreen())


class GenerateScreen(Screen):
    """Choose week and output mode, then generate."""

    BINDINGS = [
        Binding("escape", "app.pop_screen", "Back"),
        Binding("enter", "generate", "Generate", show=False),
        Binding("g", "generate", "Generate"),
    ]

    def compose(self) -> ComposeResult:
        yield Header(show_clock=False)
        yield Static("Generate Program", classes="screen-title")
        yield Rule()

        yield Static("Week", classes="section-label")
        with Container(classes="card"):
            with RadioSet(id="week-radio"):
                yield RadioButton("All weeks", id="w-all", value=True)
                for i in range(1, 7):
                    yield RadioButton(f"Week {i}", id=f"w-{i}")

        yield Static("Output format", classes="section-label")
        with Container(classes="card"):
            with RadioSet(id="mode-radio"):
                yield RadioButton("Text (clipboard)", id="m-t")
                yield RadioButton("PDF", id="m-p")
                yield RadioButton("Both", id="m-b", value=True)

        with Horizontal(classes="btn-row"):
            state = self.app.state
            if not state.skip_save:
                yield Button("Back", id="btn-back", variant="default")
            yield Button("Generate [g]", id="btn-generate", variant="primary")
        yield Footer()

    @on(Button.Pressed, "#btn-back")
    def go_back(self) -> None:
        self.app.pop_screen()

    @on(Button.Pressed, "#btn-generate")
    def action_generate(self) -> None:
        state = self.app.state

        week_rs = self.query_one("#week-radio", RadioSet)
        week_btn = week_rs.pressed_button
        wid = week_btn.id if week_btn else "w-all"
        state.week = "all" if wid == "w-all" else wid.split("-")[1]

        mode_rs = self.query_one("#mode-radio", RadioSet)
        mode_btn = mode_rs.pressed_button
        mid = mode_btn.id if mode_btn else "m-b"
        state.out_mode = mid.split("-")[1]

        self.app.push_screen(OutputScreen())


class OutputScreen(Screen):
    """Display the generated program with copy/PDF/save options."""

    BINDINGS = [
        Binding("c", "copy", "Copy", priority=True),
        Binding("p", "save_pdf", "PDF", priority=True),
        Binding("s", "save_session", "Save", priority=True),
        Binding("escape", "go_done", "Done"),
        Binding("q", "go_done", "Done", show=False),
    ]

    def compose(self) -> ComposeResult:
        state = self.app.state
        yield Header(show_clock=False)
        yield Static(state.title, classes="screen-title")
        yield Rule()
        yield TextArea(id="output-area", read_only=True)
        with Horizontal(classes="btn-row"):
            if not state.skip_save:
                yield Button("Save [s]", id="btn-save-session", variant="default")
            yield Button("Copy [c]", id="btn-copy", variant="default")
            if state.out_mode in ("p", "b"):
                yield Button("PDF [p]", id="btn-pdf", variant="default")
            yield Button("Done [esc]", id="btn-done", variant="primary")
        yield Footer()

    def on_mount(self) -> None:
        state = self.app.state
        args = argparse.Namespace(
            week=state.week,
            lifts=state.lifts,
            onerm=None,
            title=state.title,
            pdf=None,
        )
        body = build_program_markdown(args, for_pdf=False)
        self._program_text = f"# {state.title}\n\n{body}"
        self._args = args

        ta = self.query_one("#output-area", TextArea)
        ta.load_text(self._program_text)

        # Auto-copy and auto-PDF if mode set
        if state.out_mode in ("t", "b"):
            copy_to_clipboard(self._program_text)
        if state.out_mode in ("p", "b"):
            self._save_pdf()

    def _save_pdf(self) -> None:
        state = self.app.state
        try:
            pdf_body = build_program_markdown(self._args, for_pdf=True)
            pdf_path = default_pdf_path(state.title)
            pdf_path.parent.mkdir(parents=True, exist_ok=True)
            markdown_to_pdf(pdf_body, str(pdf_path), title=state.title)
            self.notify(f"PDF saved: {pdf_path.name}")
        except Exception as e:
            self.notify(f"PDF failed: {e}", severity="error")

    @on(Button.Pressed, "#btn-copy")
    def action_copy(self) -> None:
        copy_to_clipboard(self._program_text)
        self.notify("Copied to clipboard.")

    @on(Button.Pressed, "#btn-pdf")
    def action_save_pdf(self) -> None:
        self._save_pdf()

    @on(Button.Pressed, "#btn-save-session")
    def action_save_session(self) -> None:
        self.app.push_screen(SaveSessionModal())

    @on(Button.Pressed, "#btn-done")
    def action_go_done(self) -> None:
        # Pop all the way back to HomeScreen
        self.app.pop_screen_all()


class SaveSessionModal(ModalScreen):
    """Modal prompt to name and save the current session."""

    BINDINGS = [Binding("escape", "dismiss_modal", "Cancel", show=False)]

    def action_dismiss_modal(self) -> None:
        self.dismiss(None)

    def compose(self) -> ComposeResult:
        state = self.app.state
        with Container(classes="card"):
            yield Static("Save Session", classes="screen-title")
            yield Rule()
            yield Label("Session name:")
            yield Input(value=state.title, id="session-name")
            with Horizontal(classes="btn-row"):
                yield Button("Cancel", id="btn-cancel", variant="default")
                yield Button("Save", id="btn-save", variant="primary")

    @on(Button.Pressed, "#btn-cancel")
    def cancel(self) -> None:
        self.dismiss(None)

    @on(Button.Pressed, "#btn-save")
    def save(self) -> None:
        state = self.app.state
        name = self.query_one("#session-name", Input).value.strip()
        if not name:
            self.app.notify("Enter a session name.", severity="warning")
            return
        state.store.save_session(name, state.lifts)
        self.app.notify(f"Saved '{name}'.")
        self.dismiss(name)


# ---------------------------------------------------------------------------
# Main App
# ---------------------------------------------------------------------------

class TBCalcApp(App):
    """Tactical Barbell Max Strength TUI."""

    CSS = CSS
    TITLE = "Tactical Barbell"
    # q quits from any screen that doesn't consume it (i.e. not inside an Input/TextArea)
    BINDINGS = [Binding("q", "quit", "Quit")]

    def __init__(self):
        super().__init__()
        self.state = AppState()

    def on_mount(self) -> None:
        self.push_screen(HomeScreen())

    def pop_screen_all(self) -> None:
        """Pop back to the root HomeScreen and refresh."""
        while len(self.screen_stack) > 1:
            self.pop_screen()
        # Refresh home session list
        try:
            home = self.screen_stack[0]
            if isinstance(home, HomeScreen):
                home._refresh_list()
        except Exception:
            pass


def run_tui() -> None:
    """Launch the TUI application."""
    app = TBCalcApp()
    app.run()
