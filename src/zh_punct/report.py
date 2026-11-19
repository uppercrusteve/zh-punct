"""输出格式。"""

from __future__ import annotations

import json
from collections.abc import Iterable

from .rules import Diagnostic

GLYPH = {"error": "x", "warn": "!", "info": "i"}


def text(items: Iterable[Diagnostic], colors: bool = True) -> str:
    rows = []
    for item in items:
        glyph = GLYPH.get(item.severity, "-")
        rows.append(f"{item.path}:{item.line}:{item.col} {item.code} {glyph} {item.message}")
    return "\n".join(rows)


def github(items: Iterable[Diagnostic]) -> str:
    rows = []
    for item in items:
        level = "error" if item.severity == "error" else "warning"
        rows.append(
            f"::{level} file={item.path},line={item.line},col={item.col},"
            f"title=zh-punct {item.code}::{item.message}"
        )
    return "\n".join(rows)


def jsonl(items: Iterable[Diagnostic]) -> str:
    return json.dumps([item.__dict__ for item in items], ensure_ascii=False, indent=2)


FORMATS = {"text": text, "github": github, "json": jsonl}
