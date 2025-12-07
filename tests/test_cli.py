import argparse
from pathlib import Path
import sys
import builtins

import tbweightcalc.cli as cli


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
    assert "## WEEK 2 - 80%" in md
    # Squat line should be present somewhere
    assert "squat" in md.lower()
    # Should contain the separator '---' style HR since for_pdf=False and multiple weeks not used
    # (for a single week it shouldn't add extra HRs at end)
    assert "\\pagebreak" not in md  # that's PDF-only


def test_build_program_markdown_pdf_uses_pagebreaks():
    # This uses "all" weeks so there will be separators
    args = make_args(week="all")
    md = cli.build_program_markdown(args, for_pdf=True)

    # In PDF mode we expect raw \pagebreak between weeks
    assert "\\pagebreak" in md
    # No visible horizontal rules
    assert "---" not in md


# -------------------------------------------------------------------
# Tests for main() CLI behavior
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
    monkeypatch.setattr(cli, "copy_to_clipboard", lambda text: None)

    # Capture the args passed into markdown_to_pdf instead of actually running it
    called = {}

    def fake_markdown_to_pdf(markdown: str, output_path: str, title: str | None = None):
        called["markdown"] = markdown
        called["output_path"] = output_path
        called["title"] = title

        # Simulate creating a file so tests can assert existence if desired
        Path(output_path).write_bytes(b"%PDF-FAKE%")

    monkeypatch.setattr(cli, "markdown_to_pdf", fake_markdown_to_pdf)

    # Patch sys.argv for argparse
    monkeypatch.setattr(cli, "argparse", cli.argparse)
    monkeypatch.setenv("PYTHONUNBUFFERED", "1")

    # Run main with patched sys.argv
    monkeypatch.setattr(cli, "os", cli.os)
    monkeypatch.setattr(cli, "Path", cli.Path)

    # Easiest: monkeypatch sys.argv in the module
    import sys

    monkeypatch.setattr(sys, "argv", argv)

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

    called = {}

    def fake_markdown_to_pdf(markdown: str, output_path: str, title: str | None = None):
        called["markdown"] = markdown
        called["output_path"] = output_path
        called["title"] = title
        Path(output_path).write_bytes(b"%PDF-FAKE%")

    monkeypatch.setattr(cli, "markdown_to_pdf", fake_markdown_to_pdf)

    import sys

    monkeypatch.setattr(sys, "argv", argv)

    cli.main()

    captured = capsys.readouterr()
    stdout = captured.out

    # Should print a heading that starts with "# Tactical Barbell Max Strength:"
    assert "# Tactical Barbell Max Strength:" in stdout

    assert called["title"] is not None
    assert called["title"].startswith("Tactical Barbell Max Strength:")
    assert Path(called["output_path"]) == pdf_path
    assert pdf_path.exists()


def test_main_interactive_text_only(monkeypatch, capsys):
    """
    When tbcalc is run with no CLI options, it should enter interactive mode.

    In this scenario the user:
      - provides a title
      - provides squat & bench 1RMs
      - skips deadlift & WPU
      - chooses text-only output
    """

    # Simulate: tbcalc  (no args)
    monkeypatch.setattr(sys, "argv", ["tbcalc"])

    # Fake user inputs for input() prompts
    inputs = iter(
        [
            "My Interactive Title",  # title
            "455",  # squat 1RM
            "250",  # bench 1RM
            "",  # deadlift (blank -> skip)
            "",  # weighted pull-up (blank -> skip)
            "all",  # week selection
            "t",  # output: text only
        ]
    )

    def fake_input(prompt: str = "") -> str:
        return next(inputs)

    import builtins

    monkeypatch.setattr(builtins, "input", fake_input)

    # Avoid touching system clipboard in tests
    monkeypatch.setattr(cli, "copy_to_clipboard", lambda text: None)

    # Track whether markdown_to_pdf gets called (it should NOT for text-only)
    called = {"pdf": False}

    def fake_markdown_to_pdf(markdown: str, output_path: str, title: str | None = None):
        called["pdf"] = True

    monkeypatch.setattr(cli, "markdown_to_pdf", fake_markdown_to_pdf)

    # Run main()
    cli.main()

    out = capsys.readouterr().out

    # Should print the title and some program content
    assert "My Interactive Title" in out
    assert "WEEK" in out.upper()
    assert "455" in out  # squat
    assert "250" in out  # bench
    # Deadlift and WPU were skipped, so no obvious WPU numbers
    # (you can tighten this if you want more specific checks)

    # In text-only mode, we should NOT generate a PDF
    assert called["pdf"] is False


def test_main_interactive_both_generates_pdf(monkeypatch, capsys, tmp_path):
    """
    Interactive mode with 'both' output should still call markdown_to_pdf.
    """

    monkeypatch.setattr(sys, "argv", ["tbcalc"])

    inputs = iter(
        [
            "",  # title (blank -> default title)
            "455",  # squat
            "250",  # bench
            "300",  # deadlift
            "",  # WPU (skip)
            "1",  # week = 1 only
            "b",  # output: both (text + pdf)
        ]
    )

    def fake_input(prompt: str = "") -> str:
        return next(inputs)

    import builtins

    monkeypatch.setattr(builtins, "input", fake_input)
    monkeypatch.setattr(cli, "copy_to_clipboard", lambda text: None)

    # Capture markdown_to_pdf arguments
    pdf_call = {}

    def fake_markdown_to_pdf(markdown: str, output_path: str, title: str | None = None):
        pdf_call["markdown"] = markdown
        pdf_call["output_path"] = output_path
        pdf_call["title"] = title
        # Simulate file creation
        Path(output_path).write_bytes(b"%PDF-FAKE%")

    monkeypatch.setattr(cli, "markdown_to_pdf", fake_markdown_to_pdf)

    cli.main()

    out = capsys.readouterr().out

    # Should print some text for week 1 with the right lifts
    assert "Week 1" in out or "WEEK 1" in out.upper()
    assert "455" in out
    assert "250" in out
    assert "300" in out

    # PDF generation should have been invoked
    assert "output_path" in pdf_call
    assert "markdown" in pdf_call
    assert pdf_call["markdown"]  # non-empty markdown
    assert pdf_call["title"] is not None


def test_main_interactive_ctrl_c_exits_cleanly(monkeypatch, capsys):
    """
    If the user hits Ctrl-C in interactive mode, main() should
    exit cleanly without propagating KeyboardInterrupt.
    """

    # Simulate: tbcalc  (no args)
    monkeypatch.setattr(sys, "argv", ["tbcalc"])

    # First call to input() raises KeyboardInterrupt, like pressing Ctrl-C
    def fake_input(prompt: str = "") -> str:
        raise KeyboardInterrupt

    monkeypatch.setattr(builtins, "input", fake_input)

    # Make sure we don't touch clipboard or PDF in this path
    monkeypatch.setattr(cli, "copy_to_clipboard", lambda text: None)
    monkeypatch.setattr(cli, "markdown_to_pdf", lambda *a, **k: None)

    # This should NOT raise KeyboardInterrupt; it should just print a message
    cli.main()

    out = capsys.readouterr().out
    assert "Aborted by user" in out  # or whatever message you chose
