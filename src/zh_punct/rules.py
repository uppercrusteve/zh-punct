"""规则表与检查器。

每条规则只判机器有把握的形态问题；用法争议（该不该加逗号、语气）不碰。
"""

from __future__ import annotations

import bisect
import re
from dataclasses import dataclass

from .mask import CJK_CLASS, CJK_RE, SENTINEL, Masked, has_cjk

CJK_ANY = CJK_RE

@dataclass(frozen=True)
class Rule:
    code: str
    severity: str
    title: str
    fixable: bool
    detail: str


@dataclass(frozen=True)
class Diagnostic:
    path: str
    line: int
    col: int
    code: str
    severity: str
    message: str
    fix: tuple[int, int, str] | None = None

    def sort_key(self) -> tuple[int, int, str]:
        return (self.line, self.col, self.code)


RULES: dict[str, Rule] = {
    rule.code: rule
    for rule in (
        Rule("ZP001", "error", "中文里用半角标点", True,
             "中文字间夹了半角 , ; : ? ! ( ) . ，应改用全角"),
        Rule("ZP002", "warn", "纯英文语境里用全角标点", False,
             "整行没有汉字，却用了全角标点"),
        Rule("ZP003", "off", "中英文之间缺空格", True,
             "汉字与拉丁字母、数字之间没有空格"),
        Rule("ZP004", "error", "成对符号不闭合", False,
             "引号、括号、书名号开合数量不等"),
        Rule("ZP005", "error", "标点连续重复", True,
             "中文标点连写，例如 ，， 或 ！！"),
        Rule("ZP006", "warn", "省略号写法", True,
             "用 ... 或 。。。 表示省略号，应写 ……"),
        Rule("ZP007", "warn", "破折号写法", True,
             "用 -- 表示破折号，应写 ——"),
        Rule("ZP009", "warn", "标点落在行首", False,
             "句读、收尾括号等出现在换行后的行首（避头尾）"),
        Rule("ZP010", "off", "数字区间用半角波浪线", True,
             "区间 1~2 应写 1～2"),
    )
}

HALF_TO_FULL = {",": "，", ";": "；", ":": "：", "?": "？", "!": "！", "(": "（", ")": "）"}
PAIRS = (("“", "”"), ("‘", "’"), ("（", "）"), ("「", "」"),
         ("『", "』"), ("《", "》"), ("〈", "〉"), ("【", "】"))
ASCII_ALNUM = re.compile(r"[A-Za-z0-9]")
ASCII_ONLY = re.compile(r"^[\x20-\x7e\u00b2\u00b3\u00b9\u2070-\u207f\u2080-\u2089]*$")
# 参考文献行：作者之间用半角逗号是 GB/T 7714 的规定写法，不算错
REF_LINE = re.compile(r"^\s*(?:\|\s*)?\[\d+\]")

RUN_RE = re.compile(r"([，、；：？！])\1+")
DOTS_RE = re.compile(r"\.{3,}")
ELLIPSIS_RE = re.compile(r"…+")
CJK_DOTS_RE = re.compile(r"。{2,}")
DASH_RE = re.compile(r"(?<!-)--(?!-)")
TILDE_RE = re.compile(r"(?<=\d)[ \t]*~[ \t]*(?=\d)")
LEAD_PUNCT = "，。、；：？！）」』”’…—"
PUNCT_ONLY = re.compile(r"[\s，。；：？！（）“”‘’「」『』《》〈〉【】…—]+")
# 单个西文词加一个句末中文标点（如 MIT。）：本来就这么写
SINGLE_TOKEN = re.compile(r"^[!-~]+[。，]$")
SPACE_GAP = re.compile(
    f"([{CJK_CLASS}])([A-Za-z0-9])|([A-Za-z0-9])([{CJK_CLASS}])"
)


def _line_index(offset: int, starts: list[int]) -> int:
    return max(0, bisect.bisect_right(starts, offset) - 1)


def _ctx_has_cjk(line: str, index: int, span: int = 3) -> bool:
    left = line[max(0, index - span):index]
    right = line[index + 1:index + 1 + span]
    return bool(CJK_RE.search(left) or CJK_RE.search(right))


def _paren_is_ascii(line: str, index: int) -> bool:
    char = line[index]
    if char == "(":
        close = line.find(")", index + 1)
        return close != -1 and bool(ASCII_ONLY.match(line[index + 1:close]))
    if char == ")":
        open_at = line.rfind("(", 0, index)
        return open_at != -1 and bool(ASCII_ONLY.match(line[open_at + 1:index]))
    return False


def _check_line_punct(masked: Masked, path: str, out: list[Diagnostic], level: str) -> None:
    for index, (start, line) in enumerate(masked.rows):
        if index in masked.disabled_lines or not has_cjk(line):
            continue
        is_ref = bool(REF_LINE.match(line))
        for col, char in enumerate(line):
            if char not in HALF_TO_FULL and char != ".":
                continue
            prev = line[col - 1] if col else ""
            nxt = line[col + 1] if col + 1 < len(line) else ""
            if is_ref and char in ",;:":
                continue
            if char == ".":
                if CJK_ANY.match(prev or " ") and CJK_ANY.match(nxt or " "):
                    out.append(Diagnostic(
                        path, index + 1, col + 1, "ZP001", level,
                        "中文句末用半角句点，应写 。", (start + col, start + col + 1, "。")))
                continue
            if char == "!" and nxt == "[":
                continue
            if ASCII_ALNUM.match(prev or " ") and ASCII_ALNUM.match(nxt or " "):
                continue
            if char in "()" and _paren_is_ascii(line, col):
                continue
            if not _ctx_has_cjk(line, col):
                continue
            full = HALF_TO_FULL[char]
            out.append(Diagnostic(
                path, index + 1, col + 1, "ZP001", level,
                f"中文里用了半角 {char}，应写 {full}",
                (start + col, start + col + 1, full)))


def _check_fullwidth(masked: Masked, path: str, out: list[Diagnostic], level: str) -> None:
    for index, (start, line) in enumerate(masked.rows):
        if index in masked.disabled_lines or has_cjk(line):
            continue
        if PUNCT_ONLY.match(line):
            continue
        if SINGLE_TOKEN.match(line):
            continue
        for col, char in enumerate(line):
            if char in "，。；：？！（）“”‘’「」《》":
                out.append(Diagnostic(path, index + 1, col + 1, "ZP002", level,
                                      f"整行没有汉字，却用了全角 {char}"))


def _check_spacing(masked: Masked, path: str, out: list[Diagnostic], level: str) -> None:
    for index, (start, line) in enumerate(masked.rows):
        if index in masked.disabled_lines or not has_cjk(line):
            continue
        for match in SPACE_GAP.finditer(line):
            pos = match.start() + 1
            if line[pos:pos + 1] == SENTINEL:
                continue
            out.append(Diagnostic(path, index + 1, pos + 1, "ZP003", level,
                                  "汉字与西文之间加一个空格", (start + pos, start + pos, " ")))


def _check_pairs(masked: Masked, path: str, out: list[Diagnostic], level: str) -> None:
    starts = [row[0] for row in masked.rows]
    for opener, closer in PAIRS:
        stack: list[int] = []
        for offset, char in enumerate(masked.text):
            if char == opener:
                stack.append(offset)
            elif char == closer:
                if stack:
                    stack.pop()
                else:
                    line = _line_index(offset, starts)
                    out.append(Diagnostic(path, line + 1, offset - starts[line] + 1,
                                          "ZP004", level,
                                          f"{closer} 多出来，前面没有对应的 {opener}"))
        for offset in stack[:5]:
            line = _line_index(offset, starts)
            out.append(Diagnostic(path, line + 1, offset - starts[line] + 1,
                                  "ZP004", level, f"{opener} 没有闭合"))


def _check_runs(masked: Masked, path: str, out: list[Diagnostic], level: str) -> None:
    starts = [row[0] for row in masked.rows]
    for match in RUN_RE.finditer(masked.text):
        line = _line_index(match.start(), starts)
        if line in masked.disabled_lines:
            continue
        col = match.start() - starts[line] + 1
        out.append(Diagnostic(path, line + 1, col, "ZP005", level,
                              f"标点重复 {match.group(0)}",
                              (match.start(), match.end(), match.group(1))))


def _check_ellipsis(masked: Masked, path: str, out: list[Diagnostic], level: str) -> None:
    starts = [row[0] for row in masked.rows]
    for pattern in (DOTS_RE, ELLIPSIS_RE, CJK_DOTS_RE):
        for match in pattern.finditer(masked.text):
            line = _line_index(match.start(), starts)
            row = masked.line(line)
            if line in masked.disabled_lines or not has_cjk(row) or REF_LINE.match(row):
                continue
            if pattern is ELLIPSIS_RE and len(match.group(0)) != 1:
                continue
            col = match.start() - starts[line] + 1
            out.append(Diagnostic(path, line + 1, col, "ZP006", level,
                                  f"省略号写成 {match.group(0)}，应为 ……",
                                  (match.start(), match.end(), "……")))


def _check_dash(masked: Masked, path: str, out: list[Diagnostic], level: str) -> None:
    starts = [row[0] for row in masked.rows]
    for match in DASH_RE.finditer(masked.text):
        line = _line_index(match.start(), starts)
        if line in masked.disabled_lines or not has_cjk(masked.line(line)):
            continue
        col = match.start() - starts[line] + 1
        out.append(Diagnostic(path, line + 1, col, "ZP007", level,
                              "破折号写成 --，应为 ——", (match.start(), match.end(), "——")))


def _check_lead(masked: Masked, path: str, out: list[Diagnostic], level: str) -> None:
    for index, (start, line) in enumerate(masked.rows):
        if index == 0 or index in masked.disabled_lines:
            continue
        stripped = line.lstrip()
        if not stripped or stripped[0] not in LEAD_PUNCT:
            continue
        if not masked.line(index - 1).strip() or not has_cjk(masked.line(index - 1)):
            continue
        col = len(line) - len(stripped)
        out.append(Diagnostic(path, index + 1, col + 1, "ZP009", level,
                              f"{stripped[0]} 落在行首"))


def _check_tilde(masked: Masked, path: str, out: list[Diagnostic], level: str) -> None:
    starts = [row[0] for row in masked.rows]
    for match in TILDE_RE.finditer(masked.text):
        line = _line_index(match.start(), starts)
        if line in masked.disabled_lines or not has_cjk(masked.line(line)):
            continue
        col = match.start() - starts[line] + 1
        out.append(Diagnostic(path, line + 1, col, "ZP010", level,
                              "数字区间用半角 ~，应为 ～", (match.start(), match.end(), "～")))


CHECKS = (
    ("ZP001", _check_line_punct),
    ("ZP002", _check_fullwidth),
    ("ZP003", _check_spacing),
    ("ZP004", _check_pairs),
    ("ZP005", _check_runs),
    ("ZP006", _check_ellipsis),
    ("ZP007", _check_dash),
    ("ZP009", _check_lead),
    ("ZP010", _check_tilde),
)


def check_text(text: str, path: str, severities: dict[str, str] | None = None,
               markdown: bool = True) -> tuple[list[Diagnostic], Masked]:
    from .mask import mask

    masked = mask(text, markdown=markdown)
    severities = severities or {}
    found: list[Diagnostic] = []
    for code, func in CHECKS:
        level = severities.get(code, RULES[code].severity)
        if level == "off":
            continue
        func(masked, path, found, level)
    found.sort(key=Diagnostic.sort_key)
    return found, masked


def apply_fixes(text: str, diagnostics: list[Diagnostic], severities: dict[str, str]) -> str:
    """只落安全修复；区间重叠时保留靠前的一段。"""
    spans = sorted(
        {d.fix for d in diagnostics if d.fix is not None
         and RULES[d.code].fixable and severities.get(d.code, RULES[d.code].severity) != "off"},
        key=lambda span: (span[0], -(span[1] - span[0])),
    )
    chosen: list[tuple[int, int, str]] = []
    last_end = -1
    for span in spans:
        if span[0] < last_end:
            continue
        chosen.append(span)
        last_end = span[1]
    for start, end, replacement in sorted(chosen, reverse=True):
        text = text[:start] + replacement + text[end:]
    return text
