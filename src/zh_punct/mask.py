"""把不该参与检查的区域替换成哨兵，长度不变，偏移可复用。

设计取舍：掩码只做"减噪"，判规则时仍能看到相邻原文；掩掉的位置在规则里直接跳过。
宁可漏报，也不报在代码块和 URL 里。
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

SENTINEL = "\x00"

CJK_CLASS = "\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff\u3005\u3007"
CJK_RE = re.compile(f"[{CJK_CLASS}]")

FENCE_RE = re.compile(r"^[ ]{0,3}(?P<fence>`{3,}|~{3,})(?P<info>.*)$")
INLINE_CODE_RE = re.compile(r"(?P<tick>`+)(?P<body>[^\n]+?)(?P=tick)")
URL_RE = re.compile(
    r"(?:(?:https?|ftp)://|www\.)[^\s<>()（）]*[^\s<>()（）,.;:!?]"
)
EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
TAG_RE = re.compile(r"</?[A-Za-z][^<>\n]*>")
COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)
AUTOLINK_RE = re.compile(r"<[A-Za-z][\w+.-]*:[^\s<>]+>")
LINK_DEST_RE = re.compile(r"\]\([^()\n]*\)")
REF_DEF_RE = re.compile(r"^[ ]{0,3}\[[^\]]+\]:[ \t]*\S+", re.MULTILINE)
FRONT_MATTER_RE = re.compile(r"\A---\r?\n.*?\r?\n---[ \t]*(?:\r\n|\n|\Z)", re.DOTALL)

CONTROL_OFF = re.compile(r"<!--\s*zh-punct:\s*off\s*-->")
CONTROL_ON = re.compile(r"<!--\s*zh-punct:\s*on\s*-->")
LINE_OFF = re.compile(r"zh-punct:\s*skip-line\b")


@dataclass
class Masked:
    text: str
    rows: list[tuple[int, str]]
    disabled_lines: set[int] = field(default_factory=set)

    def line(self, index: int) -> str:
        return self.rows[index][1]

    def start(self, index: int) -> int:
        return self.rows[index][0]

    def __len__(self) -> int:
        return len(self.rows)


def split_rows(text: str) -> list[tuple[int, str]]:
    """返回 (行首偏移, 行内容)，行内容不含换行符。"""
    rows: list[tuple[int, str]] = []
    offset = 0
    for piece in text.splitlines(keepends=True):
        content = piece.rstrip("\r\n")
        rows.append((offset, content))
        offset += len(piece)
    if not text:
        return []
    return rows


def _blank(buf: list[str], start: int, end: int) -> None:
    for i in range(start, min(end, len(buf))):
        if buf[i] not in "\r\n":
            buf[i] = SENTINEL


def _blank_match(buf: list[str], match: re.Match[str]) -> None:
    _blank(buf, match.start(), match.end())


def _indented_code_rows(contents: list[str], markdown: bool) -> set[int]:
    if not markdown:
        return set()
    hit: set[int] = set()
    inside = False
    prev_blank = True
    for index, content in enumerate(contents):
        blank = not content.strip()
        indented = content.startswith(("    ", "\t"))
        if not blank and indented and (inside or prev_blank):
            inside = True
            hit.add(index)
        elif not blank:
            inside = False
        prev_blank = blank
    return hit


def mask(text: str, markdown: bool = True) -> Masked:
    rows = split_rows(text)
    contents = [content for _, content in rows]
    buf = list(text)
    disabled: set[int] = set()

    # 控制注释：区段开关与行尾关闭
    inside_off = False
    for index, (start, content) in enumerate(rows):
        if CONTROL_OFF.search(content):
            disabled.add(index)
            inside_off = True
            _blank(buf, start, start + len(content))
        elif CONTROL_ON.search(content):
            disabled.add(index)
            inside_off = False
            _blank(buf, start, start + len(content))
        elif inside_off:
            disabled.add(index)
            _blank(buf, start, start + len(content))
        elif LINE_OFF.search(content):
            disabled.add(index)

    if markdown:
        front = FRONT_MATTER_RE.search(text)
        if front:
            _blank(buf, front.start(), front.end())

        fence: str | None = None
        for start, content in rows:
            fence_match = FENCE_RE.match(content)
            if fence is None and fence_match:
                fence = fence_match.group("fence")[0] * 3
                _blank(buf, start, start + len(content))
            elif fence is not None:
                _blank(buf, start, start + len(content))
                if content.strip().startswith(fence):
                    fence = None

        for index in _indented_code_rows(contents, markdown):
            start, content = rows[index]
            _blank(buf, start, start + len(content))

    for match in COMMENT_RE.finditer(text):
        _blank_match(buf, match)
    for match in AUTOLINK_RE.finditer(text):
        _blank_match(buf, match)
    for match in URL_RE.finditer(text):
        _blank_match(buf, match)
    for match in EMAIL_RE.finditer(text):
        _blank_match(buf, match)
    for match in TAG_RE.finditer(text):
        _blank_match(buf, match)
    for match in LINK_DEST_RE.finditer(text):
        _blank_match(buf, match)
    for match in REF_DEF_RE.finditer(text):
        _blank_match(buf, match)
    if markdown:
        for match in INLINE_CODE_RE.finditer(text):
            _blank_match(buf, match)

    # 转义符连同被转义的字符一起掩掉
    for match in re.finditer(r"\\.", text):
        _blank(buf, match.start(), match.end())

    masked_lines = ["".join(buf[start:start + len(content)]) for start, content in rows]
    return Masked(text="".join(buf), rows=list(zip((r[0] for r in rows), masked_lines)),
                  disabled_lines=disabled)


def has_cjk(line: str) -> bool:
    return bool(CJK_RE.search(line))
