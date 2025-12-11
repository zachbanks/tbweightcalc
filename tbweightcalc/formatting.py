from __future__ import annotations

"""Helpers for rendering program output in plain text or Markdown."""

from dataclasses import dataclass


# Central registry of Markdown styles
MARKDOWN_STYLES = {
    # Inline styles
    "bold": ("**", "**"),
    "italic": ("*", "*"),
    "code": ("`", "`"),
    "strikethrough": ("~~", "~~"),
    # Heading styles (prefix-only; suffix is None)
    "h1": ("# ", None),
    "h2": ("## ", None),
    "h3": ("### ", None),
    "h4": ("#### ", None),
    "h5": ("##### ", None),
    "h6": ("###### ", None),
    "hr": ("---", None),
    "ul": ("- ", None),
}


def apply_markdown(text: str, style: str, styles: dict | None = None) -> str:
    """
    Apply a Markdown style to ``text``.

    Args:
        text: The string to wrap or prefix.
        style: A key in the styles dict (e.g. ``"bold"``, ``"h1"``, ``"code"``).
        styles: Optional styles registry; defaults to :data:`MARKDOWN_STYLES`.
    """
    if styles is None:
        styles = MARKDOWN_STYLES

    wrapper = styles.get(style)
    if wrapper is None:
        raise ValueError(f"Unknown markdown style: {style!r}")

    if isinstance(wrapper, str):
        prefix = suffix = wrapper
    else:
        prefix, suffix = wrapper

    # Prefix-only style (e.g. headings)
    if suffix is None:
        return f"{prefix}{text}"

    return f"{prefix}{text}{suffix}"


class Formatter:
    """Minimal interface for rendering text elements."""

    def heading(self, text: str, *, level: int = 1) -> str:
        raise NotImplementedError

    def list_item(self, text: str) -> str:
        raise NotImplementedError

    def bold(self, text: str) -> str:
        raise NotImplementedError

    def italic(self, text: str) -> str:
        raise NotImplementedError

    def emphasis(self, text: str) -> str:
        return self.italic(text)

    def horizontal_rule(self) -> str:
        raise NotImplementedError


@dataclass(slots=True)
class PlainFormatter(Formatter):
    """Formatter that emits plain text (no Markdown syntax)."""

    bullet: str = "• "

    def heading(self, text: str, *, level: int = 1) -> str:  # noqa: ARG002
        return text

    def list_item(self, text: str) -> str:
        return f"{self.bullet}{text}" if text else ""

    def bold(self, text: str) -> str:
        return text

    def italic(self, text: str) -> str:
        return text

    def horizontal_rule(self) -> str:
        return "-" * 10


@dataclass(slots=True)
class MarkdownFormatter(Formatter):
    """Formatter that emits Markdown-friendly text."""

    styles: dict = None

    def __post_init__(self):
        if self.styles is None:
            self.styles = MARKDOWN_STYLES

    def heading(self, text: str, *, level: int = 1) -> str:
        level = max(1, min(level, 6))
        return apply_markdown(text, f"h{level}", styles=self.styles)

    def list_item(self, text: str) -> str:
        return apply_markdown(text, "ul", styles=self.styles)

    def bold(self, text: str) -> str:
        return apply_markdown(text, "bold", styles=self.styles)

    def italic(self, text: str) -> str:
        return apply_markdown(text, "italic", styles=self.styles)

    def horizontal_rule(self) -> str:
        return apply_markdown("", "hr", styles=self.styles)
