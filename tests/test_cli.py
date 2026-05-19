import argparse
from pathlib import Path
import sys
import builtins

import pytest

from tbweightcalc import cli


# -------------------------------------------------------------------
# Tests for format_exercise_name
# -------------------------------------------------------------------


def test_format_exercise_name_rdl():
    """Test that RDL is capitalized properly."""
    assert cli.format_exercise_name("rdl") == "RDL"
    assert cli.format_exercise_name("RDL") == "RDL"
    assert cli.format_exercise_name("Rdl") == "RDL"


def test_format_exercise_name_regular():
    """Test that regular exercises use title case."""
    assert cli.format_exercise_name("squat") == "Squat"
    assert cli.format_exercise_name("bench press") == "Bench Press"
    assert cli.format_exercise_name("front squat") == "Front Squat"


def test_rdl_in_hinge_slot():
    """Test that RDL is available in the Hinge slot."""
    hinge_slot = None
    for slot in cli.INTERACTIVE_LIFT_SLOTS:
        if slot["name"] == "Hinge":
            hinge_slot = slot
            break

    assert hinge_slot is not None, "Hinge slot should exist"

    # Check that RDL is in the options
    rdl_option = None
    for opt in hinge_slot["options"]:
        if opt["exercise_name"] == "rdl":
            rdl_option = opt
            break

    assert rdl_option is not None, "RDL should be in Hinge options"
    assert rdl_option["key"] == "rdl"
    assert "RDL" in rdl_option["prompt"], "Prompt should use capitalized RDL"


# -------------------------------------------------------------------
# Small helper for build_program_markdown tests
# -------------------------------------------------------------------


def make_args(
    week: str | None = "1",
    squat: int | None = 455,
    bench: int | None = 250,
    deadlift: int | None = 300,
    weighted_pullup: tuple[int, int] | None = (252, 210),
    title: str | None = "Test Program",
    pdf: str | None = None,
) -> argparse.Namespace:
    """
    Helper to create an argparse-like Namespace for build_program_markdown.
    Uses the legacy fields that build_program_markdown still understands.
    """
    ns = argparse.Namespace()
    ns.week = week
    ns.squat = squat
    ns.bench = bench
    ns.deadlift = deadlift
    ns.weighted_pullup = list(weighted_pullup) if weighted_pullup else None
    ns.onerm = None
    ns.title = title
    ns.pdf = pdf
    return ns


# -------------------------------------------------------------------
# Tests for helper functions
# -------------------------------------------------------------------


def test_default_pdf_path_with_title(monkeypatch, tmp_path):
    # Make HOME point to a temporary directory so the path is predictable
    fake_home = tmp_path
    monkeypatch.setenv("HOME", str(fake_home))

    path = cli.default_pdf_path("My Cool Program")
    # Should live in ~/Downloads
    assert path.parent == fake_home / "Downloads"
    # Filename should be sanitized and end in .pdf
    assert path.name.startswith("My_Cool_Program")
    assert path.suffix == ".pdf"


def test_default_pdf_path_adds_pdf_extension(monkeypatch, tmp_path):
    fake_home = tmp_path
    monkeypatch.setenv("HOME", str(fake_home))

    path = cli.default_pdf_path("NoExtensionTitle")
    assert path.suffix == ".pdf"


def test_build_program_markdown_single_week_screen():
    args = make_args(week="2")  # only week 2
    md = cli.build_program_markdown(args, for_pdf=False)

    # Should include a WEEK 2 header as an H2
    assert "WEEK 2 - 80%" in md
    # Should not contain PDF-only pagebreak markers
    assert "\\pagebreak" not in md


def test_build_program_markdown_pdf_uses_pagebreaks():
    # This uses "all" weeks so there will be separators
    args = make_args(week="all")
    md = cli.build_program_markdown(args, for_pdf=True)

    # In PDF mode we expect raw \pagebreak between weeks
    assert "\\pagebreak" in md
    # We don't expect visible '---' HRs from our HR helper in PDF mode
    assert "---" not in md


# -------------------------------------------------------------------
# Tests for main() CLI behavior (non-interactive paths)
# -------------------------------------------------------------------


def test_main_prints_title_and_calls_markdown_to_pdf(monkeypatch, capsys, tmp_path):
    """
    Test the full CLI main() without actually generating a PDF or hitting pbcopy.
    """

    # Fake arguments as if called from command line:
    # tbcalc -dl 300 -sq 455 -bp 250 -wpu 252 210 --title "CLI Test" --pdf <tmp_path>
    pdf_path = tmp_path / "cli_test.pdf"
    argv = [
        "tbcalc",
        "-dl",
        "300",
        "-sq",
        "455",
        "-bp",
        "250",
        "-wpu",
        "252",
        "210",
        "--title",
        "CLI Test",
        "--pdf",
        str(pdf_path),
    ]

    # Avoid real clipboard and keep argparse/os/Path in module
    monkeypatch.setattr(cli, "copy_to_clipboard", lambda text: None)
    monkeypatch.setattr(sys, "argv", argv)

    # Capture the args passed into markdown_to_pdf instead of actually running it
    called = {}

    def fake_markdown_to_pdf(markdown: str, output_path: str, title: str | None = None):
        called["markdown"] = markdown
        called["output_path"] = output_path
        called["title"] = title

        # Simulate creating a file so tests can assert existence if desired
        Path(output_path).write_bytes(b"%PDF-FAKE%")

    monkeypatch.setattr(cli, "markdown_to_pdf", fake_markdown_to_pdf)

    cli.main()

    # Check stdout
    captured = capsys.readouterr()
    stdout = captured.out

    assert "CLI Test" in stdout
    assert "[PDF saved to:" in stdout

    # Verify markdown_to_pdf was called with expected title and path
    assert called["title"] == "CLI Test"
    assert Path(called["output_path"]) == pdf_path
    assert pdf_path.exists()
    assert called["markdown"]  # non-empty markdown content


def test_main_uses_default_title_when_not_provided(monkeypatch, capsys, tmp_path):
    """
    When --title is not passed, main() should use the default
    'Tactical Barbell Max Strength: YYYY-MM-DD'.
    """
    pdf_path = tmp_path / "no_title.pdf"
    argv = [
        "tbcalc",
        "-dl",
        "300",
        "-sq",
        "455",
        "-bp",
        "250",
        "-wpu",
        "252",
        "210",
        "--pdf",
        str(pdf_path),
    ]

    monkeypatch.setattr(cli, "copy_to_clipboard", lambda text: None)
    monkeypatch.setattr(sys, "argv", argv)

    called = {}

    def fake_markdown_to_pdf(markdown: str, output_path: str, title: str | None = None):
        called["markdown"] = markdown
        called["output_path"] = output_path
        called["title"] = title
        Path(output_path).write_bytes(b"%PDF-FAKE%")

    monkeypatch.setattr(cli, "markdown_to_pdf", fake_markdown_to_pdf)

    cli.main()

    captured = capsys.readouterr()
    stdout = captured.out

    # Should print a heading that starts with the default title
    assert "Tactical Barbell Max Strength:" in stdout

    assert called["title"] is not None
    assert called["title"].startswith("Tactical Barbell Max Strength:")
    assert Path(called["output_path"]) == pdf_path
    assert pdf_path.exists()


def test_main_calls_run_tui_when_no_args(monkeypatch):
    """
    When tbcalc is run with no CLI arguments (other than the program name),
    main() should launch the TUI instead of parsing flags.
    """
    from tbweightcalc import tui as _tui_mod

    called = {"run_tui": False}

    def fake_run_tui():
        called["run_tui"] = True

    # Patch run_tui on the already-imported tui module so the inline
    # "from tbweightcalc.tui import run_tui" inside main() picks it up.
    monkeypatch.setattr(_tui_mod, "run_tui", fake_run_tui)
    monkeypatch.setattr(sys, "argv", ["tbcalc"])

    cli.main()

    assert called["run_tui"] is True


# -------------------------------------------------------------------
# Tests for 1RM prompt / helpers
# -------------------------------------------------------------------


def test_prompt_one_rm(monkeypatch, capsys):
    inputs = iter(["275", "5"])

    def fake_input(prompt: str = "") -> str:
        return next(inputs)

    monkeypatch.setattr(builtins, "input", fake_input)
    # avoid real clipboard
    monkeypatch.setattr(cli, "copy_to_clipboard", lambda text: None)

    cli.prompt_one_rm()

    out = capsys.readouterr().out
    assert "Estimated 1RM" in out
    # With Epley & rounding you've been using: 275 * (1 + 5/30) = 275 * 7/6 ≈ 321
    assert "321" in out


def test_prompt_one_rm_copies_numeric_result_to_clipboard(monkeypatch, capsys):
    """
    prompt_one_rm should:
      - read weight & reps from input()
      - print the estimated 1RM
      - copy ONLY the numeric 1RM to the clipboard
    """

    # Simulate user typing: weight=275, reps=5
    inputs = iter(["275", "5"])

    def fake_input(prompt: str = "") -> str:
        return next(inputs)

    monkeypatch.setattr(builtins, "input", fake_input)

    copied = {}

    def fake_copy(text: str) -> None:
        copied["value"] = text

    # Avoid touching the real clipboard
    monkeypatch.setattr(cli, "copy_to_clipboard", fake_copy)

    # Run the prompt
    cli.prompt_one_rm()

    out = capsys.readouterr().out

    # 275 x 5 with your Epley + rounding logic -> 321 lb
    assert "Estimated 1RM" in out
    assert "321 lb" in out

    # Clipboard should contain ONLY the number "321"
    assert copied["value"] == "321"


# -------------------------------------------------------------------
# Tests for parse_one_rm_string
# -------------------------------------------------------------------


class TestParseOneRmString:
    def test_blank_returns_none(self):
        assert cli.parse_one_rm_string("") is None
        assert cli.parse_one_rm_string("   ") is None

    def test_single_integer_treated_as_known_1rm(self):
        assert cli.parse_one_rm_string("455") == 455
        assert cli.parse_one_rm_string("  300  ") == 300

    def test_weight_and_reps_space_separated(self):
        # 240 x 5 -> Epley: 240 * (1 + 5/30) = 240 * 7/6 = 280
        result = cli.parse_one_rm_string("240 5")
        assert result == 280

    def test_weight_and_reps_with_x_separator(self):
        # 240x5 -> 280 as above
        assert cli.parse_one_rm_string("240x5") == 280
        assert cli.parse_one_rm_string("240X5") == 280

    def test_invalid_input_returns_none(self):
        assert cli.parse_one_rm_string("abc") is None
        assert cli.parse_one_rm_string("240 x") is None
        assert cli.parse_one_rm_string("240 5 3") is None

    def test_reps_with_x_separator_and_spaces(self):
        # Base expectation using '240x5'
        base = cli.parse_one_rm_string("240x5")
        assert base is not None

        # Variants that should behave identically
        assert cli.parse_one_rm_string("240 x5") == base
        assert cli.parse_one_rm_string("240x 5") == base
        assert cli.parse_one_rm_string("240 x 5") == base

    def test_decimal_weights_rounded(self):
        # Decimal 1RM values should be rounded to nearest int
        assert cli.parse_one_rm_string("255.6") == 256
        assert cli.parse_one_rm_string("255.4") == 255
        assert cli.parse_one_rm_string("255.5") == 256  # Python rounds to even, but close enough

        # Decimal weights with reps
        # 240.5 x 5 -> Epley: 240.5 * (1 + 5/30) = 240.5 * 7/6 ≈ 280.583 -> 281
        assert cli.parse_one_rm_string("240.5 5") == 281
        assert cli.parse_one_rm_string("240.5x5") == 281

    def test_math_expression_percentage_addition(self):
        # 240 + 10% -> 240 + 24 = 264
        assert cli.parse_one_rm_string("240 + 10%") == 264
        assert cli.parse_one_rm_string("240+10%") == 264
        assert cli.parse_one_rm_string("240 +10%") == 264
        assert cli.parse_one_rm_string("240+ 10%") == 264

    def test_math_expression_percentage_subtraction(self):
        # 240 - 5% -> 240 - 12 = 228
        assert cli.parse_one_rm_string("240 - 5%") == 228
        assert cli.parse_one_rm_string("240-5%") == 228
        assert cli.parse_one_rm_string("240 -5%") == 228
        assert cli.parse_one_rm_string("240- 5%") == 228

    def test_math_expression_absolute_addition(self):
        # 240 + 20 -> 260
        assert cli.parse_one_rm_string("240 + 20") == 260
        assert cli.parse_one_rm_string("240+20") == 260
        # With 'lbs' suffix
        assert cli.parse_one_rm_string("240 + 20 lbs") == 260
        assert cli.parse_one_rm_string("240+20lbs") == 260
        assert cli.parse_one_rm_string("240 + 20 lb") == 260

    def test_math_expression_absolute_subtraction(self):
        # 240 - 10 -> 230
        assert cli.parse_one_rm_string("240 - 10") == 230
        assert cli.parse_one_rm_string("240-10") == 230
        # With 'lbs' suffix
        assert cli.parse_one_rm_string("240 - 10 lbs") == 230
        assert cli.parse_one_rm_string("240-10lbs") == 230
        assert cli.parse_one_rm_string("240 - 10 lb") == 230

    def test_math_expression_with_decimals(self):
        # 240.5 + 10% -> 240.5 + 24.05 = 264.55 -> 265
        assert cli.parse_one_rm_string("240.5 + 10%") == 265
        # 240 + 5.5 -> 245.5 -> 246
        assert cli.parse_one_rm_string("240 + 5.5") == 246
        # 240 - 2.3% -> 240 - 5.52 = 234.48 -> 234
        assert cli.parse_one_rm_string("240 - 2.3%") == 234

    def test_math_expression_edge_cases(self):
        # Large percentage
        assert cli.parse_one_rm_string("200 + 50%") == 300
        # Small percentage
        assert cli.parse_one_rm_string("100 + 1%") == 101
        # Subtraction that results in lower value
        assert cli.parse_one_rm_string("300 - 100") == 200


# -------------------------------------------------------------------
# Tests for math expression support in parse_one_rm_string
# -------------------------------------------------------------------


class TestMathExpressions:
    def test_percentage_addition(self):
        # 240 + 10% -> 240 + 24 = 264
        assert cli.parse_one_rm_string("240 + 10%") == 264
        assert cli.parse_one_rm_string("240+10%") == 264
        assert cli.parse_one_rm_string("240 +10%") == 264
        assert cli.parse_one_rm_string("240+ 10%") == 264

    def test_percentage_subtraction(self):
        # 240 - 5% -> 240 - 12 = 228
        assert cli.parse_one_rm_string("240 - 5%") == 228
        assert cli.parse_one_rm_string("240-5%") == 228
        assert cli.parse_one_rm_string("240 -5%") == 228
        assert cli.parse_one_rm_string("240- 5%") == 228

    def test_absolute_addition(self):
        # 380 + 5 -> 385
        assert cli.parse_one_rm_string("380 + 5") == 385
        assert cli.parse_one_rm_string("380+5") == 385
        # with lbs suffix
        assert cli.parse_one_rm_string("240 + 20 lbs") == 260
        assert cli.parse_one_rm_string("240+20lbs") == 260
        assert cli.parse_one_rm_string("240 + 20 lb") == 260

    def test_absolute_subtraction(self):
        # 380 - 10 -> 370
        assert cli.parse_one_rm_string("380 - 10") == 370
        assert cli.parse_one_rm_string("380-10") == 370
        # with lbs suffix
        assert cli.parse_one_rm_string("240 - 10 lbs") == 230
        assert cli.parse_one_rm_string("240-10lbs") == 230
        assert cli.parse_one_rm_string("240 - 10 lb") == 230

    def test_percentage_subtraction_deload(self):
        # 380 - 10% -> 380 * 0.10 = 38; 380 - 38 = 342
        assert cli.parse_one_rm_string("380 - 10%") == 342

    def test_decimal_base_and_adjustment(self):
        # 240.5 + 10% -> 240.5 + 24.05 = 264.55 -> 265
        assert cli.parse_one_rm_string("240.5 + 10%") == 265
        # 240 + 5.5 -> 245.5 -> 246
        assert cli.parse_one_rm_string("240 + 5.5") == 246
        # 240 - 2.3% -> 240 - 5.52 = 234.48 -> 234
        assert cli.parse_one_rm_string("240 - 2.3%") == 234

    def test_edge_cases(self):
        assert cli.parse_one_rm_string("200 + 50%") == 300
        assert cli.parse_one_rm_string("100 + 1%") == 101
        assert cli.parse_one_rm_string("300 - 100") == 200

    def test_evaluate_weight_expression_directly(self):
        assert cli.evaluate_weight_expression(240, "+ 10%") == 264.0
        assert cli.evaluate_weight_expression(240, "- 5%") == 228.0
        assert cli.evaluate_weight_expression(240, "+ 20") == 260.0
        assert cli.evaluate_weight_expression(240, "- 10 lbs") == 230.0


# -------------------------------------------------------------------
# Tests for parse_weighted_pullup_string + interactive WPU helper
# -------------------------------------------------------------------


class TestParseWeightedPullupString:
    def test_blank_and_whitespace_return_none(self):
        assert cli.parse_weighted_pullup_string(200, "") is None
        assert cli.parse_weighted_pullup_string(200, "   ") is None

    def test_numeric_two_part_and_x_style(self):
        bw = 200

        # '35 4'  -> +35 for 4 reps  => 235 x 4
        r1 = cli.parse_weighted_pullup_string(bw, "35 4")
        # Epley: 235 * (1 + 4/30) ≈ 266
        assert r1 == 266

        # '35x4'  -> +35 for 4 reps  => 235 x 4
        r2 = cli.parse_weighted_pullup_string(bw, "35x4")
        assert r2 == 266

        # '35X4'  -> case-insensitive
        r3 = cli.parse_weighted_pullup_string(bw, "35X4")
        assert r3 == 266

    def test_bw_shorthands(self):
        bw = 200

        # 'bw' -> bodyweight for 1 rep => 200
        r1 = cli.parse_weighted_pullup_string(bw, "bw")
        assert r1 == 200

        # 'bw 4' -> BW for 4 reps => 200 x 4
        r2 = cli.parse_weighted_pullup_string(bw, "bw 4")
        # 200 * (1 + 4/30) ≈ 227
        assert r2 == 227

        # 'bwx4' -> BW for 4 reps
        r3 = cli.parse_weighted_pullup_string(bw, "bwx4")
        assert r3 == 227

        # 'bw x 4' with a space before x
        r4 = cli.parse_weighted_pullup_string(bw, "bw x 4")
        assert r4 == 227

    def test_zero_added_weight(self):
        bw = 200

        # '0 4' -> bodyweight-only for 4 reps
        r = cli.parse_weighted_pullup_string(bw, "0 4")
        # same as bw 4
        assert r == 227

    def test_single_number_means_one_rep_added_weight(self):
        """
        '45' should be interpreted as +45 lb for 1 rep.
        For bodyweight 200:
          total = 245 x 1 -> estimated 1RM should be 245.
        """
        bw = 200
        r = cli.parse_weighted_pullup_string(bw, "45")
        assert r == 245

    def test_invalid_strings_return_none(self):
        bw = 200
        assert cli.parse_weighted_pullup_string(bw, "foo") is None
        assert cli.parse_weighted_pullup_string(bw, "35x") is None
        assert cli.parse_weighted_pullup_string(bw, "x4") is None
        assert cli.parse_weighted_pullup_string(bw, "35 4 x") is None

    def test_numeric_x_separator_with_spaces(self):
        bw = 200

        base = cli.parse_weighted_pullup_string(bw, "35x4")
        assert base is not None

        assert cli.parse_weighted_pullup_string(bw, "35 x4") == base
        assert cli.parse_weighted_pullup_string(bw, "35x 4") == base
        assert cli.parse_weighted_pullup_string(bw, "35 x 4") == base

    def test_decimal_added_weights_rounded(self):
        bw = 200

        # Decimal added weight for 1 rep: 200 + 45.5 = 245.5 x 1 -> 246
        assert cli.parse_weighted_pullup_string(bw, "45.5") == 246

        # Decimal added weight with reps: (200 + 35.5) x 4 = 235.5 x 4
        # Epley: 235.5 * (1 + 4/30) ≈ 266.9 -> 267
        assert cli.parse_weighted_pullup_string(bw, "35.5 4") == 267
        assert cli.parse_weighted_pullup_string(bw, "35.5x4") == 267


class TestPromptWeightedPullupInteractive:
    def test_reprompts_on_invalid_bodyweight_then_skip(self, monkeypatch, capsys):
        """
        If bodyweight input is invalid, it should reprompt until valid or blank.
        Here:
          1) 'abc'  -> invalid
          2) ''     -> skip entirely -> returns (None, None)
        """
        inputs = iter(["abc", ""])

        def fake_input(prompt: str = "") -> str:
            return next(inputs)

        monkeypatch.setattr(builtins, "input", fake_input)

        one_rm, bw = cli.prompt_weighted_pullup_interactive()
        out = capsys.readouterr().out

        assert "Invalid bodyweight" in out
        assert one_rm is None
        assert bw is None

    def test_valid_bodyweight_then_blank_wpu_skips_set(self, monkeypatch, capsys):
        """
        If bodyweight is valid but WPU set input is blank, we should return
        (None, bodyweight).
        """
        inputs = iter(["200", ""])

        def fake_input(prompt: str = "") -> str:
            return next(inputs)

        monkeypatch.setattr(builtins, "input", fake_input)

        one_rm, bw = cli.prompt_weighted_pullup_interactive()

        # No WPU performance, but we know bodyweight
        assert one_rm is None
        assert bw == 200

    def test_invalid_wpu_input_reprompts_until_valid(self, monkeypatch, capsys):
        """
        If bodyweight is valid but the WPU string is invalid,
        the function should reprompt until valid or blank.
        """
        # Inputs:
        #   1) '200'     -> valid bodyweight
        #   2) 'foobar'  -> invalid WPU string
        #   3) '35 4'    -> +35 lb for 4 reps
        inputs = iter(["200", "foobar", "35 4"])

        def fake_input(prompt: str = "") -> str:
            return next(inputs)

        monkeypatch.setattr(builtins, "input", fake_input)

        one_rm, bw = cli.prompt_weighted_pullup_interactive()
        out = capsys.readouterr().out

        # bodyweight should be recorded
        assert bw == 200

        # 35 4 -> total 235 x 4 -> 266 as above
        assert one_rm == 266

        assert "Could not parse weighted pull-up input" in out

    def test_accepts_single_number_as_one_rep_in_interactive(self, monkeypatch, capsys):
        """
        Ensure that the interactive helper also supports the '45' shorthand
        (extra 45 for 1 rep).
        """
        # Inputs:
        #   1) '200' -> bodyweight
        #   2) '45'  -> +45 x 1
        inputs = iter(["200", "45"])

        def fake_input(prompt: str = "") -> str:
            return next(inputs)

        monkeypatch.setattr(builtins, "input", fake_input)

        one_rm, bw = cli.prompt_weighted_pullup_interactive()

        assert bw == 200
        assert one_rm == 245  # 200 + 45 for 1 rep


# -------------------------------------------------------------------
# Fixtures + tests for interactive templates (run_interactive)
# -------------------------------------------------------------------


@pytest.fixture
def no_side_effects(monkeypatch, tmp_path):
    """
    Disable clipboard + PDF side effects, and capture args passed into
    build_program_markdown for inspection. Also isolates the session store
    so tests don't read/write the real sessions file.
    """
    from tbweightcalc.sessions import SessionStore

    captured = {}

    def fake_copy_to_clipboard(_text: str) -> None:
        return

    def fake_markdown_to_pdf(_md: str, _path: str, title: str | None = None) -> None:
        return

    def fake_build_program_markdown(
        args: argparse.Namespace, for_pdf: bool = False
    ) -> str:
        captured["args"] = args
        return "# TEST PROGRAM"

    # Use a fresh, empty session store backed by a temp file
    empty_store = SessionStore(path=tmp_path / "sessions.json")
    monkeypatch.setattr(cli, "SessionStore", lambda: empty_store)

    monkeypatch.setattr(cli, "copy_to_clipboard", fake_copy_to_clipboard)
    monkeypatch.setattr(cli, "markdown_to_pdf", fake_markdown_to_pdf)
    monkeypatch.setattr(cli, "build_program_markdown", fake_build_program_markdown)

    return captured


def test_interactive_template_classic_builds_expected_lifts(
    monkeypatch, no_side_effects
):
    """
    Template 1: Classic – Squat / Bench / Deadlift / (optional) WPU
    """
    captured = no_side_effects

    # Inputs sequence:
    # 1.  title (blank -> default)
    # 2.  template = "1"
    # 3.  squat 1RM
    # 4.  squat bar weight (blank -> 45, no label prompt when blank)
    # 5.  bench 1RM
    # 6.  bench bar weight (blank -> 45)
    # 7.  deadlift 1RM
    # 8.  deadlift bar weight (blank -> 45)
    # 9.  WPU bodyweight (blank -> skip)
    # 10. review -> continue
    # 11. week (blank -> all)
    # 12. output mode "t" (text only)
    # 13. save session (blank -> skip)
    inputs = iter(
        [
            "",  # title
            "1",  # template choice -> Classic
            "455",  # squat 1RM
            "",  # squat bar weight -> default 45 (blank = default, no label prompt)
            "315",  # bench 1RM
            "",  # bench bar weight -> default 45
            "500",  # deadlift 1RM
            "",  # deadlift bar weight -> default 45
            "",  # WPU bodyweight skip
            "c",  # review -> continue without changes
            "",  # week -> "all"
            "t",  # output mode
            "",  # save session -> skip
        ]
    )

    def fake_input(prompt: str = "") -> str:
        return next(inputs)

    monkeypatch.setattr(builtins, "input", fake_input)

    cli.run_interactive()

    args = captured["args"]
    lifts = {l["exercise"]: l for l in args.lifts}

    assert lifts["squat"]["one_rm"] == 455
    assert lifts["bench press"]["one_rm"] == 315
    assert lifts["deadlift"]["one_rm"] == 500
    # No WPU because we skipped BW
    assert "weighted pullup" not in lifts


def test_interactive_template_front_squat_block_builds_expected_lifts(
    monkeypatch, no_side_effects
):
    """
    Template 2: Front-squat Block – Front Squat / Overhead Press / Deadlift / (optional) WPU
    """
    captured = no_side_effects

    inputs = iter(
        [
            "FS Block",  # title
            "2",  # template choice -> Front-squat Block
            "355",  # front squat 1RM
            "",  # front squat bar weight -> default 45 (blank = default, no label prompt)
            "185",  # overhead press 1RM
            "",  # overhead press bar weight -> default 45
            "495",  # deadlift 1RM
            "",  # deadlift bar weight -> default 45
            "200",  # WPU bodyweight
            "35x4",  # WPU set
            "c",  # review -> continue without changes
            "3",  # week = 3
            "t",  # output mode
            "",  # save session -> skip
        ]
    )

    def fake_input(prompt: str = "") -> str:
        return next(inputs)

    monkeypatch.setattr(builtins, "input", fake_input)

    cli.run_interactive()

    args = captured["args"]
    lifts = {l["exercise"]: l for l in args.lifts}

    assert "squat" not in lifts
    assert "bench press" not in lifts
    assert lifts["front squat"]["one_rm"] == 355
    assert lifts["overhead press"]["one_rm"] == 185
    assert lifts["deadlift"]["one_rm"] == 495
    # WPU should be present with estimated 1RM and given BW
    assert "weighted pullup" in lifts
    assert lifts["weighted pullup"]["body_weight"] == 200


def test_interactive_template_zercher_block_builds_expected_lifts(
    monkeypatch, no_side_effects
):
    """
    Template 3: Zercher Block – Zercher Squat / Bench Press / Deadlift / (optional) WPU
    """
    captured = no_side_effects

    inputs = iter(
        [
            "Zercher Block",  # title
            "3",  # template choice -> Zercher Block
            "315",  # zercher squat 1RM
            "",  # zercher squat bar weight -> default 45 (blank = default, no label prompt)
            "225",  # bench press 1RM
            "",  # bench press bar weight -> default 45
            "405",  # deadlift 1RM
            "",  # deadlift bar weight -> default 45
            "",  # WPU bodyweight skip
            "c",  # review -> continue without changes
            "",  # week -> "all"
            "t",  # output mode
            "",  # save session -> skip
        ]
    )

    def fake_input(prompt: str = "") -> str:
        return next(inputs)

    monkeypatch.setattr(builtins, "input", fake_input)

    cli.run_interactive()

    args = captured["args"]
    lifts = {l["exercise"]: l for l in args.lifts}

    assert "squat" not in lifts
    assert "front squat" not in lifts
    assert lifts["zercher squat"]["one_rm"] == 315
    assert lifts["bench press"]["one_rm"] == 225
    assert lifts["deadlift"]["one_rm"] == 405
    # No WPU because we skipped BW
    assert "weighted pullup" not in lifts


def test_interactive_template_custom_with_extra_exercises(
    monkeypatch, no_side_effects
):
    """
    Template 4: Custom with extra exercises added
    """
    captured = no_side_effects

    inputs = iter(
        [
            "Custom Program",  # title
            "4",  # template choice -> Custom
            # Lower-body main lift slot
            "1",  # choose squat
            "455",  # squat 1RM
            "",  # squat bar weight -> default 45 (blank = default, no label prompt)
            # Upper-body main press slot
            "1",  # choose bench press
            "315",  # bench 1RM
            "",  # bench bar weight -> default 45
            # Hinge slot
            "1",  # choose deadlift
            "500",  # deadlift 1RM
            "",  # deadlift bar weight -> default 45
            "",  # WPU bodyweight skip
            # Extra exercises
            "y",  # add extra exercises? yes
            "5",  # select overhead press (5th in EXERCISE_PROFILES keys alphabetically)
            "185",  # overhead press 1RM
            "",  # overhead press bar weight -> default 45
            "y",  # add another? yes
            "2",  # select front squat (2nd in EXERCISE_PROFILES keys alphabetically)
            "355",  # front squat 1RM
            "",  # front squat bar weight -> default 45
            "n",  # add another? no
            "c",  # review -> continue without changes
            "",  # week -> "all"
            "t",  # output mode
            "",  # save session -> skip
        ]
    )

    def fake_input(prompt: str = "") -> str:
        return next(inputs)

    monkeypatch.setattr(builtins, "input", fake_input)

    cli.run_interactive()

    args = captured["args"]
    lifts = {l["exercise"]: l for l in args.lifts}

    # Standard slot selections
    assert lifts["squat"]["one_rm"] == 455
    assert lifts["bench press"]["one_rm"] == 315
    assert lifts["deadlift"]["one_rm"] == 500
    # Extra exercises added
    assert "overhead press" in lifts
    assert lifts["overhead press"]["one_rm"] == 185
    assert "front squat" in lifts
    assert lifts["front squat"]["one_rm"] == 355
    # No WPU because we skipped BW
    assert "weighted pullup" not in lifts


# -------------------------------------------------------------------
# Tests for _review_and_edit_lifts  (review/edit step)
# -------------------------------------------------------------------


class TestReviewAndEditLifts:
    """Unit tests for the _review_and_edit_lifts helper."""

    def _make_lifts(self):
        return [
            {"exercise": "squat",      "one_rm": 455, "body_weight": None, "bar_weight": 45.0, "bar_label": None},
            {"exercise": "bench press","one_rm": 275, "body_weight": None, "bar_weight": 45.0, "bar_label": None},
            {"exercise": "deadlift",   "one_rm": 380, "body_weight": None, "bar_weight": 45.0, "bar_label": None},
        ]

    def test_continue_immediately_returns_lifts_unchanged(self, monkeypatch):
        """Typing 'c' on first prompt returns the lifts unmodified."""
        lifts = self._make_lifts()
        inputs = iter(["c"])
        monkeypatch.setattr(builtins, "input", lambda _="": next(inputs))

        result = cli._review_and_edit_lifts(lifts)

        assert result[0]["one_rm"] == 455
        assert result[1]["one_rm"] == 275
        assert result[2]["one_rm"] == 380

    def test_blank_enter_also_continues(self, monkeypatch):
        """Pressing Enter (blank) on the review prompt also continues."""
        lifts = self._make_lifts()
        inputs = iter([""])
        monkeypatch.setattr(builtins, "input", lambda _="": next(inputs))

        result = cli._review_and_edit_lifts(lifts)
        assert result is lifts  # same list returned

    def test_edit_first_lift_updates_one_rm(self, monkeypatch):
        """
        Typing '1' selects lift 1; new 1RM is applied; 'c' then continues.
        Sequence: edit lift 1 → squat prompt → new 1RM → bar → label → 'c'
        """
        lifts = self._make_lifts()
        inputs = iter([
            "1",     # edit lift 1 (squat)
            "465",   # new squat 1RM
            "",      # bar weight -> keep 45
            "",      # bar label  -> none
            "c",     # done
        ])
        monkeypatch.setattr(builtins, "input", lambda _="": next(inputs))

        result = cli._review_and_edit_lifts(lifts)

        assert result[0]["one_rm"] == 465
        assert result[1]["one_rm"] == 275  # unchanged
        assert result[2]["one_rm"] == 380  # unchanged

    def test_edit_lift_with_custom_bar(self, monkeypatch):
        """
        Editing a lift can also update its bar weight and label.
        """
        lifts = self._make_lifts()
        inputs = iter([
            "3",          # edit lift 3 (deadlift)
            "405",        # new deadlift 1RM
            "60",         # new bar weight (Trap Bar)
            "Trap Bar",   # bar label
            "c",          # done
        ])
        monkeypatch.setattr(builtins, "input", lambda _="": next(inputs))

        result = cli._review_and_edit_lifts(lifts)

        assert result[2]["one_rm"] == 405
        assert result[2]["bar_weight"] == 60.0
        assert result[2]["bar_label"] == "Trap Bar"

    def test_edit_wpu_updates_added_weight_and_bw(self, monkeypatch):
        """
        Editing a WPU entry re-prompts bodyweight and set string.
        total_1rm = BW + added = 212 + 85 = 297 stored.
        """
        lifts = [
            {"exercise": "squat",         "one_rm": 455, "body_weight": None, "bar_weight": 45.0, "bar_label": None},
            {"exercise": "weighted pullup","one_rm": 297, "body_weight": 212, "bar_weight": 45.0, "bar_label": None},
        ]
        inputs = iter([
            "2",      # edit WPU
            "",       # keep bodyweight (212)
            "45 5",   # new WPU set: +45 lb for 5 reps
            "c",      # done
        ])
        monkeypatch.setattr(builtins, "input", lambda _="": next(inputs))

        result = cli._review_and_edit_lifts(lifts)

        # New total = BW(212) + 45 for 5 reps -> Epley(257, 5)
        assert result[1]["body_weight"] == 212
        assert result[1]["one_rm"] > 297  # should be higher since 45 > 85 added

    def test_invalid_choice_then_valid_continues(self, monkeypatch, capsys):
        """
        Non-numeric input shows an error; valid number then 'c' works normally.
        """
        lifts = self._make_lifts()
        inputs = iter([
            "foo",   # invalid
            "abc",   # invalid
            "1",     # edit lift 1
            "460",   # new 1RM
            "",      # bar weight
            "",      # bar label
            "c",     # done
        ])
        monkeypatch.setattr(builtins, "input", lambda _="": next(inputs))

        result = cli._review_and_edit_lifts(lifts)
        out = capsys.readouterr().out

        assert "Enter a lift number" in out
        assert result[0]["one_rm"] == 460

    def test_out_of_range_number_shows_error(self, monkeypatch, capsys):
        """Choosing a number outside the list range shows an error and loops."""
        lifts = self._make_lifts()
        inputs = iter([
            "9",   # out of range (only 3 lifts)
            "c",   # then continue
        ])
        monkeypatch.setattr(builtins, "input", lambda _="": next(inputs))

        result = cli._review_and_edit_lifts(lifts)
        out = capsys.readouterr().out

        assert "between 1 and 3" in out
        assert result[0]["one_rm"] == 455  # unchanged

    def test_empty_lifts_returns_immediately(self, monkeypatch):
        """Empty lift list skips the review entirely."""
        called = []
        monkeypatch.setattr(builtins, "input", lambda _="": called.append(1) or "c")

        result = cli._review_and_edit_lifts([])

        assert result == []
        assert len(called) == 0  # input never called


def test_interactive_review_edits_squat_before_generating(
    monkeypatch, no_side_effects
):
    """
    Integration: user enters squat 1RM as 455, then at the review screen
    edits it to 465 before continuing.
    """
    captured = no_side_effects

    inputs = iter([
        "",      # title -> default
        "1",     # template -> Classic
        "455",   # squat 1RM
        "",      # squat bar weight (blank -> 45, no label prompt)
        "275",   # bench 1RM
        "",      # bench bar weight
        "500",   # deadlift 1RM
        "",      # deadlift bar weight
        "",      # WPU skip
        # --- review step ---
        "1",     # edit lift 1 (squat)
        "465",   # corrected squat 1RM
        "",      # bar weight keep (blank -> 45, no label prompt)
        "c",     # done reviewing
        # --- continue ---
        "",      # week -> all
        "t",     # output mode
        "",      # save session -> skip
    ])

    monkeypatch.setattr(builtins, "input", lambda _="": next(inputs))
    cli.run_interactive()

    lifts = {l["exercise"]: l for l in captured["args"].lifts}
    assert lifts["squat"]["one_rm"] == 465   # corrected value
    assert lifts["bench press"]["one_rm"] == 275
    assert lifts["deadlift"]["one_rm"] == 500


# -------------------------------------------------------------------
# Tests for prompt_bar_weight (saved bars recall)
# -------------------------------------------------------------------

class TestPromptBarWeight:
    """Unit tests for prompt_bar_weight with saved bar store."""

    def test_default_returns_45_no_label(self, monkeypatch, tmp_path):
        from tbweightcalc.sessions import SessionStore
        store = SessionStore(path=tmp_path / "s.json")
        inputs = iter([""])  # blank -> default 45
        monkeypatch.setattr(builtins, "input", lambda _="": next(inputs))
        weight, label = cli.prompt_bar_weight("squat", store=store)
        assert weight == 45.0
        assert label is None

    def test_custom_weight_with_label(self, monkeypatch, tmp_path):
        from tbweightcalc.sessions import SessionStore
        store = SessionStore(path=tmp_path / "s.json")
        inputs = iter(["60", "Trap Bar", "n"])  # weight, label, don't save
        monkeypatch.setattr(builtins, "input", lambda _="": next(inputs))
        weight, label = cli.prompt_bar_weight("deadlift", store=store)
        assert weight == 60.0
        assert label == "Trap Bar"

    def test_select_saved_bar_by_index(self, monkeypatch, tmp_path):
        from tbweightcalc.sessions import SessionStore
        store = SessionStore(path=tmp_path / "s.json")
        store.save_bar("Trap Bar", 60)
        store.save_bar("C-70", 35)
        inputs = iter(["2"])  # pick second saved bar
        monkeypatch.setattr(builtins, "input", lambda _="": next(inputs))
        weight, label = cli.prompt_bar_weight("deadlift", store=store)
        assert weight == 35.0
        assert label == "C-70"

    def test_save_new_bar_when_prompted(self, monkeypatch, tmp_path):
        from tbweightcalc.sessions import SessionStore
        store = SessionStore(path=tmp_path / "s.json")
        inputs = iter(["60", "Trap Bar", "y"])  # weight, label, save yes
        monkeypatch.setattr(builtins, "input", lambda _="": next(inputs))
        cli.prompt_bar_weight("deadlift", store=store)
        bars = store.list_bars()
        assert len(bars) == 1
        assert bars[0]["name"] == "Trap Bar"
        assert bars[0]["weight"] == 60.0

    def test_no_save_prompt_without_store(self, monkeypatch):
        inputs = iter(["60", "My Bar"])  # weight, label — no save prompt
        monkeypatch.setattr(builtins, "input", lambda _="": next(inputs))
        weight, label = cli.prompt_bar_weight("squat")
        assert weight == 60.0
        assert label == "My Bar"

    def test_no_save_prompt_for_default_weight(self, monkeypatch, tmp_path):
        from tbweightcalc.sessions import SessionStore
        store = SessionStore(path=tmp_path / "s.json")
        # 45# with a label — should NOT prompt to save (standard bar)
        inputs = iter(["45", "Standard Bar"])
        monkeypatch.setattr(builtins, "input", lambda _="": next(inputs))
        weight, label = cli.prompt_bar_weight("squat", store=store)
        assert weight == 45.0
        assert label == "Standard Bar"
        assert store.list_bars() == []


# -------------------------------------------------------------------
# Tests for _prompt_save_session (title auto-fill)
# -------------------------------------------------------------------

class TestPromptSaveSession:
    """Unit tests for _prompt_save_session default name behaviour."""

    def _store(self, tmp_path):
        from tbweightcalc.sessions import SessionStore
        return SessionStore(path=tmp_path / "s.json")

    LIFTS = [{"exercise": "squat", "one_rm": 455, "body_weight": None, "bar_weight": 45.0, "bar_label": None}]

    def test_enter_uses_default_name(self, monkeypatch, tmp_path):
        store = self._store(tmp_path)
        monkeypatch.setattr(builtins, "input", lambda _="": "")
        cli._prompt_save_session(self.LIFTS, store, default_name="TB2026-02 Home")
        sessions = store.list_sessions()
        assert len(sessions) == 1
        assert sessions[0]["name"] == "TB2026-02 Home"

    def test_custom_name_overrides_default(self, monkeypatch, tmp_path):
        store = self._store(tmp_path)
        monkeypatch.setattr(builtins, "input", lambda _="": "My Custom Name")
        cli._prompt_save_session(self.LIFTS, store, default_name="TB2026-02 Home")
        sessions = store.list_sessions()
        assert sessions[0]["name"] == "My Custom Name"

    def test_n_skips_save(self, monkeypatch, tmp_path):
        store = self._store(tmp_path)
        monkeypatch.setattr(builtins, "input", lambda _="": "n")
        cli._prompt_save_session(self.LIFTS, store, default_name="TB2026-02 Home")
        assert store.list_sessions() == []

    def test_blank_without_default_skips(self, monkeypatch, tmp_path):
        store = self._store(tmp_path)
        monkeypatch.setattr(builtins, "input", lambda _="": "")
        cli._prompt_save_session(self.LIFTS, store)
        assert store.list_sessions() == []

    def test_title_auto_fill_in_interactive(self, monkeypatch, tmp_path, no_side_effects):
        """Title entered by user becomes the default session name."""
        from tbweightcalc.sessions import SessionStore
        store = SessionStore(path=tmp_path / "s.json")
        monkeypatch.setattr(cli, "SessionStore", lambda: store)

        inputs = iter([
            "TB2026-02 Home",  # title
            "1",               # template -> Classic
            "455",             # squat 1RM
            "",                # squat bar weight (blank -> 45, no label prompt)
            "275",             # bench 1RM
            "",                # bench bar weight
            "500",             # deadlift 1RM
            "",                # deadlift bar weight
            "",                # skip WPU
            "c",               # review done
            "",                # week all
            "t",               # text only
            "",                # save session -> Enter accepts default title
        ])
        monkeypatch.setattr(builtins, "input", lambda _="": next(inputs))
        cli.run_interactive()

        sessions = store.list_sessions()
        assert len(sessions) == 1
        assert sessions[0]["name"] == "TB2026-02 Home"


# -------------------------------------------------------------------
# Tests for direct-output from loaded session
# -------------------------------------------------------------------

SAVED_LIFTS = [
    {"exercise": "squat", "one_rm": 455, "body_weight": None, "bar_weight": 45.0, "bar_label": None},
    {"exercise": "bench press", "one_rm": 275, "body_weight": None, "bar_weight": 45.0, "bar_label": None},
    {"exercise": "deadlift", "one_rm": 500, "body_weight": None, "bar_weight": 45.0, "bar_label": None},
]


def test_loaded_session_direct_output_skips_edit(monkeypatch, tmp_path, no_side_effects):
    """Loading a session and pressing Enter outputs directly without edit."""
    from tbweightcalc.sessions import SessionStore
    store = SessionStore(path=tmp_path / "s.json")
    store.save_session("Home Block", SAVED_LIFTS)
    monkeypatch.setattr(cli, "SessionStore", lambda: store)

    inputs = iter([
        "1",    # load session 1
        "",     # edit or output -> default 'o' (direct output, no title/save prompts)
        "",     # week -> all
        "t",    # text only
    ])
    monkeypatch.setattr(builtins, "input", lambda _="": next(inputs))
    captured = no_side_effects
    cli.run_interactive()

    args = captured["args"]
    lifts = {l["exercise"]: l for l in args.lifts}
    assert lifts["squat"]["one_rm"] == 455
    assert lifts["bench press"]["one_rm"] == 275
    assert lifts["deadlift"]["one_rm"] == 500


def test_loaded_session_edit_choice_enters_edit_flow(monkeypatch, tmp_path, no_side_effects):
    """Loading a session and choosing 'e' prompts for title then enters review."""
    from tbweightcalc.sessions import SessionStore
    store = SessionStore(path=tmp_path / "s.json")
    store.save_session("Home Block", SAVED_LIFTS)
    monkeypatch.setattr(cli, "SessionStore", lambda: store)

    inputs = iter([
        "1",    # load session 1
        "e",    # edit first
        "",     # title -> use session name
        "c",    # review -> continue without changes
        "",     # week -> all
        "t",    # text only
        "",     # save -> skip
    ])
    monkeypatch.setattr(builtins, "input", lambda _="": next(inputs))
    captured = no_side_effects
    cli.run_interactive()

    args = captured["args"]
    lifts = {l["exercise"]: l for l in args.lifts}
    assert lifts["squat"]["one_rm"] == 455


def test_loaded_session_direct_output_title_preserved(monkeypatch, tmp_path, no_side_effects):
    """Session name is used as title when outputting directly (no title/save prompts)."""
    from tbweightcalc.sessions import SessionStore
    store = SessionStore(path=tmp_path / "s.json")
    store.save_session("TB2026-04 Home", SAVED_LIFTS)
    monkeypatch.setattr(cli, "SessionStore", lambda: store)

    inputs = iter([
        "1",    # load session
        "",     # direct output (no title prompt, no save prompt)
        "",     # week -> all
        "t",    # text only
    ])
    monkeypatch.setattr(builtins, "input", lambda _="": next(inputs))
    captured = no_side_effects
    cli.run_interactive()

    args = captured["args"]
    assert args.title == "TB2026-04 Home"


def test_loaded_session_edit_custom_title(monkeypatch, tmp_path, no_side_effects):
    """In edit mode, a custom title overrides the session name."""
    from tbweightcalc.sessions import SessionStore
    store = SessionStore(path=tmp_path / "s.json")
    store.save_session("Home Block", SAVED_LIFTS)
    monkeypatch.setattr(cli, "SessionStore", lambda: store)

    inputs = iter([
        "1",            # load session
        "e",            # edit first
        "New Title",    # custom title
        "c",            # review -> continue
        "",             # week -> all
        "t",            # text only
        "",             # save -> skip
    ])
    monkeypatch.setattr(builtins, "input", lambda _="": next(inputs))
    captured = no_side_effects
    cli.run_interactive()

    assert captured["args"].title == "New Title"


# -------------------------------------------------------------------
# Tests for duplicate session
# -------------------------------------------------------------------

def test_duplicate_session_default_title(monkeypatch, tmp_path, no_side_effects):
    """Duplicate mode pre-fills title as 'Copy of <session name>'."""
    from tbweightcalc.sessions import SessionStore
    store = SessionStore(path=tmp_path / "s.json")
    store.save_session("Home Block", SAVED_LIFTS)
    monkeypatch.setattr(cli, "SessionStore", lambda: store)

    inputs = iter([
        "1",    # load session
        "d",    # duplicate
        "",     # title -> accept default "Copy of Home Block"
        "",     # skip adjustment
        "c",    # review -> continue
        "",     # week -> all
        "t",    # text only
        "",     # save -> accept default title
    ])
    monkeypatch.setattr(builtins, "input", lambda _="": next(inputs))
    captured = no_side_effects
    cli.run_interactive()

    assert captured["args"].title == "Copy of Home Block"


def test_duplicate_session_custom_title(monkeypatch, tmp_path, no_side_effects):
    """Duplicate mode accepts a custom title."""
    from tbweightcalc.sessions import SessionStore
    store = SessionStore(path=tmp_path / "s.json")
    store.save_session("Home Block", SAVED_LIFTS)
    monkeypatch.setattr(cli, "SessionStore", lambda: store)

    inputs = iter([
        "1",            # load session
        "d",            # duplicate
        "Gym Block",    # custom title
        "",             # skip adjustment
        "c",            # review -> continue
        "",             # week -> all
        "t",            # text only
        "",             # save -> accept default title
    ])
    monkeypatch.setattr(builtins, "input", lambda _="": next(inputs))
    captured = no_side_effects
    cli.run_interactive()

    assert captured["args"].title == "Gym Block"


def test_duplicate_session_saves_as_new_session(monkeypatch, tmp_path, no_side_effects):
    """Duplicate saves a new session without touching the original."""
    from tbweightcalc.sessions import SessionStore
    store = SessionStore(path=tmp_path / "s.json")
    store.save_session("Home Block", SAVED_LIFTS)
    monkeypatch.setattr(cli, "SessionStore", lambda: store)

    inputs = iter([
        "1",                   # load session
        "d",                   # duplicate
        "",                    # title -> "Copy of Home Block"
        "",                    # skip adjustment
        "c",                   # review -> continue
        "",                    # week -> all
        "t",                   # text only
        "Copy of Home Block",  # save -> confirm name
    ])
    monkeypatch.setattr(builtins, "input", lambda _="": next(inputs))
    cli.run_interactive()

    sessions = store.list_sessions()
    names = [s["name"] for s in sessions]
    assert "Home Block" in names
    assert "Copy of Home Block" in names
    assert len(sessions) == 2


def test_duplicate_session_lifts_match_original(monkeypatch, tmp_path, no_side_effects):
    """Duplicated session carries the same lifts as the original."""
    from tbweightcalc.sessions import SessionStore
    store = SessionStore(path=tmp_path / "s.json")
    store.save_session("Home Block", SAVED_LIFTS)
    monkeypatch.setattr(cli, "SessionStore", lambda: store)

    inputs = iter([
        "1",    # load session
        "d",    # duplicate
        "",     # title -> "Copy of Home Block"
        "",     # skip adjustment
        "c",    # review -> continue
        "",     # week -> all
        "t",    # text only
        "",     # save -> skip
    ])
    monkeypatch.setattr(builtins, "input", lambda _="": next(inputs))
    captured = no_side_effects
    cli.run_interactive()

    lifts = {l["exercise"]: l for l in captured["args"].lifts}
    assert lifts["squat"]["one_rm"] == 455
    assert lifts["bench press"]["one_rm"] == 275
    assert lifts["deadlift"]["one_rm"] == 500


# -------------------------------------------------------------------
# Tests for delete session from interactive list
# -------------------------------------------------------------------

def test_delete_session_by_number(monkeypatch, tmp_path, no_side_effects):
    """'del 1' at the session prompt deletes that session, re-shows list, then starts fresh."""
    from tbweightcalc.sessions import SessionStore
    store = SessionStore(path=tmp_path / "s.json")
    store.save_session("Home Block", SAVED_LIFTS)
    store.save_session("Gym Block", SAVED_LIFTS)
    monkeypatch.setattr(cli, "SessionStore", lambda: store)

    inputs = iter([
        "del 1",    # delete session 1 ("Home Block")
        "",         # re-shown list -> Enter to start fresh
        "",         # title -> default
        "1",        # template -> Classic
        "455",      # squat 1RM
        "",         # squat bar weight
        "275",      # bench 1RM
        "",         # bench bar weight
        "500",      # deadlift 1RM
        "",         # deadlift bar weight
        "",         # skip WPU
        "c",        # review -> continue
        "",         # week -> all
        "t",        # text only
        "n",        # save -> no
    ])
    monkeypatch.setattr(builtins, "input", lambda _="": next(inputs))
    cli.run_interactive()

    sessions = store.list_sessions()
    names = [s["name"] for s in sessions]
    assert "Home Block" not in names
    assert "Gym Block" in names


def test_delete_session_by_name(monkeypatch, tmp_path, no_side_effects):
    """'del Gym Block' at the session prompt deletes by name then re-shows list."""
    from tbweightcalc.sessions import SessionStore
    store = SessionStore(path=tmp_path / "s.json")
    store.save_session("Home Block", SAVED_LIFTS)
    store.save_session("Gym Block", SAVED_LIFTS)
    monkeypatch.setattr(cli, "SessionStore", lambda: store)

    inputs = iter([
        "del Gym Block",  # delete by name
        "",               # re-shown list -> Enter to start fresh
        "",               # title -> default
        "1",              # template -> Classic
        "455",            # squat 1RM
        "",               # squat bar weight
        "275",            # bench 1RM
        "",               # bench bar weight
        "500",            # deadlift 1RM
        "",               # deadlift bar weight
        "",               # skip WPU
        "c",              # review -> continue
        "",               # week -> all
        "t",              # text only
        "n",              # save -> no
    ])
    monkeypatch.setattr(builtins, "input", lambda _="": next(inputs))
    cli.run_interactive()

    sessions = store.list_sessions()
    names = [s["name"] for s in sessions]
    assert "Gym Block" not in names
    assert "Home Block" in names


def test_delete_session_not_found(monkeypatch, tmp_path, no_side_effects, capsys):
    """'del <unknown>' prints an error, re-shows list, then continues."""
    from tbweightcalc.sessions import SessionStore
    store = SessionStore(path=tmp_path / "s.json")
    store.save_session("Home Block", SAVED_LIFTS)
    monkeypatch.setattr(cli, "SessionStore", lambda: store)

    inputs = iter([
        "del NoSuchSession",  # bad name
        "",                   # re-shown list -> Enter to start fresh
        "",                   # title -> default
        "1",                  # template -> Classic
        "455",                # squat 1RM
        "",                   # squat bar weight
        "275",                # bench 1RM
        "",                   # bench bar weight
        "500",                # deadlift 1RM
        "",                   # deadlift bar weight
        "",                   # skip WPU
        "c",                  # review -> continue
        "",                   # week -> all
        "t",                  # text only
        "n",                  # save -> no
    ])
    monkeypatch.setattr(builtins, "input", lambda _="": next(inputs))
    cli.run_interactive()

    out = capsys.readouterr().out
    assert "No session found" in out
    # Original session untouched
    assert len(store.list_sessions()) == 1


# -------------------------------------------------------------------
# Test trailing newlines after text output
# -------------------------------------------------------------------

def test_text_output_ends_with_two_newlines(monkeypatch, tmp_path, no_side_effects, capsys):
    """Text output is followed by two blank lines."""
    from tbweightcalc.sessions import SessionStore
    store = SessionStore(path=tmp_path / "s.json")
    store.save_session("Home Block", SAVED_LIFTS)
    monkeypatch.setattr(cli, "SessionStore", lambda: store)

    inputs = iter([
        "1",    # load session
        "",     # direct output
        "",     # week -> all
        "t",    # text only
    ])
    monkeypatch.setattr(builtins, "input", lambda _="": next(inputs))
    cli.run_interactive()

    out = capsys.readouterr().out
    assert out.endswith("\n\n\n")  # program text ends \n, then print() adds \n, print() adds \n


# -------------------------------------------------------------------
# Tests for _apply_lift_adjustment
# -------------------------------------------------------------------

class TestApplyLiftAdjustment:
    LIFTS = [
        {"exercise": "squat",      "one_rm": 400, "body_weight": None, "bar_weight": 45.0, "bar_label": None},
        {"exercise": "bench press","one_rm": 300, "body_weight": None, "bar_weight": 45.0, "bar_label": None},
        {"exercise": "deadlift",   "one_rm": 500, "body_weight": None, "bar_weight": 45.0, "bar_label": None},
    ]

    def test_global_positive(self):
        result = cli._apply_lift_adjustment(self.LIFTS, 5.0)
        assert result[0]["one_rm"] == round(400 * 1.05)  # 420
        assert result[1]["one_rm"] == round(300 * 1.05)  # 315
        assert result[2]["one_rm"] == round(500 * 1.05)  # 525

    def test_global_negative(self):
        result = cli._apply_lift_adjustment(self.LIFTS, -5.0)
        assert result[0]["one_rm"] == round(400 * 0.95)  # 380
        assert result[1]["one_rm"] == round(300 * 0.95)  # 285
        assert result[2]["one_rm"] == round(500 * 0.95)  # 475

    def test_global_2_5_pct(self):
        result = cli._apply_lift_adjustment(self.LIFTS, 2.5)
        assert result[0]["one_rm"] == round(400 * 1.025)  # 410
        assert result[1]["one_rm"] == round(300 * 1.025)  # 308
        assert result[2]["one_rm"] == round(500 * 1.025)  # 513

    def test_global_10_pct(self):
        result = cli._apply_lift_adjustment(self.LIFTS, 10.0)
        assert result[0]["one_rm"] == round(400 * 1.10)  # 440
        assert result[1]["one_rm"] == round(300 * 1.10)  # 330
        assert result[2]["one_rm"] == round(500 * 1.10)  # 550

    def test_specific_exercise(self):
        result = cli._apply_lift_adjustment(self.LIFTS, 5.0, exercise="squat")
        assert result[0]["one_rm"] == round(400 * 1.05)  # 420 — adjusted
        assert result[1]["one_rm"] == 300               # unchanged
        assert result[2]["one_rm"] == 500               # unchanged

    def test_specific_exercise_case_insensitive(self):
        result = cli._apply_lift_adjustment(self.LIFTS, 10.0, exercise="Bench Press")
        assert result[0]["one_rm"] == 400               # unchanged
        assert result[1]["one_rm"] == round(300 * 1.10) # 330 — adjusted
        assert result[2]["one_rm"] == 500               # unchanged

    def test_original_lifts_not_mutated(self):
        original = [dict(l) for l in self.LIFTS]
        cli._apply_lift_adjustment(self.LIFTS, 5.0)
        for orig, after in zip(original, self.LIFTS):
            assert orig["one_rm"] == after["one_rm"]

    def test_body_weight_never_modified(self):
        lifts = [{"exercise": "weighted pullup", "one_rm": 297, "body_weight": 212, "bar_weight": 45.0, "bar_label": None}]
        result = cli._apply_lift_adjustment(lifts, 10.0)
        assert result[0]["body_weight"] == 212

    def test_wpu_applies_pct_to_added_portion_not_full_1rm(self):
        # WPU: 1RM=286, BW=212 → added portion = 74#
        # +5% on added portion: round(74 * 1.05) = 78 → new 1RM = 212 + 78 = 290
        # NOT round(286 * 1.05) = 300 (which would be wrong)
        lifts = [{"exercise": "weighted pullup", "one_rm": 286, "body_weight": 212, "bar_weight": 45.0, "bar_label": None}]
        result = cli._apply_lift_adjustment(lifts, 5.0)
        assert result[0]["one_rm"] == 212 + round(74 * 1.05)   # 290
        assert result[0]["one_rm"] != round(286 * 1.05)        # not 300

    def test_zero_pct_no_change(self):
        result = cli._apply_lift_adjustment(self.LIFTS, 0.0)
        for orig, adj in zip(self.LIFTS, result):
            assert orig["one_rm"] == adj["one_rm"]


# -------------------------------------------------------------------
# Tests for _prompt_adjustment (interactive)
# -------------------------------------------------------------------

class TestPromptAdjustment:
    LIFTS = [
        {"exercise": "squat",      "one_rm": 400, "body_weight": None, "bar_weight": 45.0, "bar_label": None},
        {"exercise": "bench press","one_rm": 300, "body_weight": None, "bar_weight": 45.0, "bar_label": None},
    ]

    def test_skip_returns_unchanged(self, monkeypatch):
        monkeypatch.setattr(builtins, "input", lambda _="": "")
        result = cli._prompt_adjustment(self.LIFTS)
        assert result[0]["one_rm"] == 400
        assert result[1]["one_rm"] == 300

    def test_preset_1_plus_2_5(self, monkeypatch):
        inputs = iter(["1", ""])  # preset +2.5%, all lifts
        monkeypatch.setattr(builtins, "input", lambda _="": next(inputs))
        result = cli._prompt_adjustment(self.LIFTS)
        assert result[0]["one_rm"] == round(400 * 1.025)
        assert result[1]["one_rm"] == round(300 * 1.025)

    def test_preset_2_plus_5(self, monkeypatch):
        inputs = iter(["2", ""])  # preset +5%, all lifts
        monkeypatch.setattr(builtins, "input", lambda _="": next(inputs))
        result = cli._prompt_adjustment(self.LIFTS)
        assert result[0]["one_rm"] == round(400 * 1.05)
        assert result[1]["one_rm"] == round(300 * 1.05)

    def test_preset_3_plus_10(self, monkeypatch):
        inputs = iter(["3", ""])  # preset +10%, all lifts
        monkeypatch.setattr(builtins, "input", lambda _="": next(inputs))
        result = cli._prompt_adjustment(self.LIFTS)
        assert result[0]["one_rm"] == round(400 * 1.10)

    def test_preset_4_minus_2_5(self, monkeypatch):
        inputs = iter(["4", ""])  # preset -2.5%, all lifts
        monkeypatch.setattr(builtins, "input", lambda _="": next(inputs))
        result = cli._prompt_adjustment(self.LIFTS)
        assert result[0]["one_rm"] == round(400 * 0.975)

    def test_preset_5_minus_5(self, monkeypatch):
        inputs = iter(["5", ""])
        monkeypatch.setattr(builtins, "input", lambda _="": next(inputs))
        result = cli._prompt_adjustment(self.LIFTS)
        assert result[0]["one_rm"] == round(400 * 0.95)

    def test_preset_6_minus_10(self, monkeypatch):
        inputs = iter(["6", ""])
        monkeypatch.setattr(builtins, "input", lambda _="": next(inputs))
        result = cli._prompt_adjustment(self.LIFTS)
        assert result[0]["one_rm"] == round(400 * 0.90)

    def test_custom_pct(self, monkeypatch):
        inputs = iter(["7", "7.5", ""])  # custom 7.5%, all lifts
        monkeypatch.setattr(builtins, "input", lambda _="": next(inputs))
        result = cli._prompt_adjustment(self.LIFTS)
        assert result[0]["one_rm"] == round(400 * 1.075)

    def test_specific_exercise_by_index(self, monkeypatch):
        inputs = iter(["2", "1"])  # +5%, apply to exercise 1 (squat)
        monkeypatch.setattr(builtins, "input", lambda _="": next(inputs))
        result = cli._prompt_adjustment(self.LIFTS)
        assert result[0]["one_rm"] == round(400 * 1.05)  # squat adjusted
        assert result[1]["one_rm"] == 300                # bench unchanged

    def test_specific_exercise_by_name(self, monkeypatch):
        inputs = iter(["2", "bench"])  # +5%, apply to bench
        monkeypatch.setattr(builtins, "input", lambda _="": next(inputs))
        result = cli._prompt_adjustment(self.LIFTS)
        assert result[0]["one_rm"] == 400                # squat unchanged
        assert result[1]["one_rm"] == round(300 * 1.05) # bench adjusted

    def test_invalid_choice_skips(self, monkeypatch):
        monkeypatch.setattr(builtins, "input", lambda _="": "xyz")
        result = cli._prompt_adjustment(self.LIFTS)
        assert result[0]["one_rm"] == 400

    def test_invalid_custom_pct_skips(self, monkeypatch):
        inputs = iter(["7", "notanumber"])
        monkeypatch.setattr(builtins, "input", lambda _="": next(inputs))
        result = cli._prompt_adjustment(self.LIFTS)
        assert result[0]["one_rm"] == 400


# -------------------------------------------------------------------
# Integration: duplicate with adjustment in run_interactive
# -------------------------------------------------------------------

def test_duplicate_with_global_adjustment(monkeypatch, tmp_path, no_side_effects):
    """Duplicate + +5% global adjustment raises all 1RMs."""
    from tbweightcalc.sessions import SessionStore
    store = SessionStore(path=tmp_path / "s.json")
    store.save_session("Home Block", SAVED_LIFTS)
    monkeypatch.setattr(cli, "SessionStore", lambda: store)

    inputs = iter([
        "1",    # load session
        "d",    # duplicate
        "",     # title -> "Copy of Home Block"
        "2",    # preset +5%
        "",     # apply to all
        "c",    # review -> continue
        "",     # week -> all
        "t",    # text only
        "",     # save -> skip
    ])
    monkeypatch.setattr(builtins, "input", lambda _="": next(inputs))
    captured = no_side_effects
    cli.run_interactive()

    lifts = {l["exercise"]: l for l in captured["args"].lifts}
    assert lifts["squat"]["one_rm"] == round(455 * 1.05)
    assert lifts["bench press"]["one_rm"] == round(275 * 1.05)
    assert lifts["deadlift"]["one_rm"] == round(500 * 1.05)


def test_duplicate_with_specific_exercise_adjustment(monkeypatch, tmp_path, no_side_effects):
    """Duplicate + adjustment on only squat leaves other lifts unchanged."""
    from tbweightcalc.sessions import SessionStore
    store = SessionStore(path=tmp_path / "s.json")
    store.save_session("Home Block", SAVED_LIFTS)
    monkeypatch.setattr(cli, "SessionStore", lambda: store)

    inputs = iter([
        "1",    # load session
        "d",    # duplicate
        "",     # title -> "Copy of Home Block"
        "2",    # preset +5%
        "1",    # apply to exercise 1 (squat)
        "c",    # review -> continue
        "",     # week -> all
        "t",    # text only
        "",     # save -> skip
    ])
    monkeypatch.setattr(builtins, "input", lambda _="": next(inputs))
    captured = no_side_effects
    cli.run_interactive()

    lifts = {l["exercise"]: l for l in captured["args"].lifts}
    assert lifts["squat"]["one_rm"] == round(455 * 1.05)
    assert lifts["bench press"]["one_rm"] == 275   # unchanged
    assert lifts["deadlift"]["one_rm"] == 500       # unchanged


def test_duplicate_skip_adjustment(monkeypatch, tmp_path, no_side_effects):
    """Duplicate with no adjustment leaves 1RMs unchanged."""
    from tbweightcalc.sessions import SessionStore
    store = SessionStore(path=tmp_path / "s.json")
    store.save_session("Home Block", SAVED_LIFTS)
    monkeypatch.setattr(cli, "SessionStore", lambda: store)

    inputs = iter([
        "1",    # load session
        "d",    # duplicate
        "",     # title -> "Copy of Home Block"
        "",     # skip adjustment
        "c",    # review -> continue
        "",     # week -> all
        "t",    # text only
        "",     # save -> skip
    ])
    monkeypatch.setattr(builtins, "input", lambda _="": next(inputs))
    captured = no_side_effects
    cli.run_interactive()

    lifts = {l["exercise"]: l for l in captured["args"].lifts}
    assert lifts["squat"]["one_rm"] == 455
    assert lifts["bench press"]["one_rm"] == 275
    assert lifts["deadlift"]["one_rm"] == 500
