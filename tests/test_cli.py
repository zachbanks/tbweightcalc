import argparse
from pathlib import Path

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


def test_main_prints_title_and_calls_markdown_to_pdf(
    monkeypatch, capsys, tmp_path
):
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


def test_main_uses_default_title_when_not_provided(
    monkeypatch, capsys, tmp_path
):
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
