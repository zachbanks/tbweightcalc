"""Minimal YAML loader for the config files used in this project.

This is intentionally small: it supports the subset of YAML used by the
bundled/default config files and the tests (nested mappings, lists, booleans,
null, quoted strings, integers, and floats).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Iterator


def safe_load(stream: Any) -> Any:
    """Parse a limited YAML document into Python data structures."""

    if hasattr(stream, "read"):
        text = stream.read()
    else:
        text = str(stream)

    lines = _preprocess(text)
    if not lines:
        return None

    parser = _Parser(lines)
    return parser.parse_block(0)


def _preprocess(text: str) -> list[tuple[int, str]]:
    lines: list[tuple[int, str]] = []
    for raw in text.splitlines():
        line = raw.rstrip()
        if not line.strip():
            continue
        stripped = line.lstrip()
        if stripped.startswith("#"):
            continue

        content = _strip_inline_comment(line)
        if not content.strip():
            continue

        indent = len(content) - len(content.lstrip(" "))
        lines.append((indent, content.strip()))

    return lines


def _strip_inline_comment(line: str) -> str:
    in_single = False
    in_double = False
    for idx, ch in enumerate(line):
        if ch == "'" and not in_double:
            in_single = not in_single
        elif ch == '"' and not in_single:
            in_double = not in_double
        elif ch == "#" and not in_single and not in_double:
            if idx == 0 or line[idx - 1].isspace():
                return line[:idx].rstrip()
    return line


@dataclass
class _Parser:
    lines: list[tuple[int, str]]
    index: int = 0

    def parse_block(self, indent: int) -> Any:
        items: list[Any] = []
        mapping: dict[Any, Any] = {}
        is_list: bool | None = None

        while self.index < len(self.lines):
            line_indent, content = self.lines[self.index]
            if line_indent < indent:
                break
            if line_indent > indent:
                raise ValueError("Invalid YAML indentation")

            if content.startswith("- "):
                if is_list is False:
                    raise ValueError("Mixed mapping and sequence at same level")
                is_list = True
                self.index += 1
                item_text = content[2:].strip()
                if not item_text:
                    items.append(self.parse_block(indent + 2))
                    continue

                if self._next_is_child(indent):
                    child = self.parse_block(indent + 2)
                    if item_text.endswith(":"):
                        key = self._parse_key(item_text[:-1].strip())
                        items.append({key: child})
                    else:
                        raise ValueError("Unsupported nested list item")
                else:
                    items.append(self._parse_value(item_text))
                continue

            if is_list is True:
                raise ValueError("Mixed sequence and mapping at same level")
            is_list = False

            key, value = self._split_mapping(content)
            self.index += 1

            if value == "":
                if self._next_is_child(indent):
                    mapping[self._parse_key(key)] = self.parse_block(indent + 2)
                else:
                    mapping[self._parse_key(key)] = {}
            else:
                mapping[self._parse_key(key)] = self._parse_value(value)

        if is_list:
            return items
        return mapping

    def _next_is_child(self, indent: int) -> bool:
        if self.index >= len(self.lines):
            return False
        next_indent, _ = self.lines[self.index]
        return next_indent > indent

    @staticmethod
    def _split_mapping(content: str) -> tuple[str, str]:
        if ":" not in content:
            raise ValueError("Expected mapping entry")
        key, value = content.split(":", 1)
        return key.strip(), value.strip()

    @staticmethod
    def _parse_key(text: str) -> Any:
        return _parse_scalar(text, allow_bare_string=True)

    @staticmethod
    def _parse_value(text: str) -> Any:
        text = text.strip()
        if text.startswith("[") and text.endswith("]"):
            inner = text[1:-1].strip()
            if not inner:
                return []
            return [_parse_scalar(part.strip()) for part in _split_inline_list(inner)]
        return _parse_scalar(text)


def _split_inline_list(text: str) -> list[str]:
    parts: list[str] = []
    current: list[str] = []
    in_single = False
    in_double = False

    for ch in text:
        if ch == "'" and not in_double:
            in_single = not in_single
        elif ch == '"' and not in_single:
            in_double = not in_double
        elif ch == "," and not in_single and not in_double:
            parts.append("".join(current).strip())
            current = []
            continue
        current.append(ch)

    if current:
        parts.append("".join(current).strip())
    return parts


def _parse_scalar(text: str, allow_bare_string: bool = False) -> Any:
    if text == "":
        return ""

    if text.startswith('"') and text.endswith('"'):
        return text[1:-1].replace('\\"', '"')
    if text.startswith("'") and text.endswith("'"):
        return text[1:-1].replace("\\'", "'")

    lowered = text.lower()
    if lowered == "true":
        return True
    if lowered == "false":
        return False
    if lowered in {"null", "none", "~"}:
        return None

    try:
        if any(ch in text for ch in (".", "e", "E")):
            return float(text)
        return int(text)
    except ValueError:
        return text if allow_bare_string else text
