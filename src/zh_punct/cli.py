"""命令行入口。"""

from __future__ import annotations

import argparse
import fnmatch
import os
import sys
from pathlib import Path

from . import __version__
from .report import FORMATS
from .rules import RULES, apply_fixes, check_text

DEFAULT_EXTS = {".md", ".markdown", ".txt", ".rst", ".tex", ".org"}
IGNORE_FILE = ".zhpunctignore"
SKIP_DIRS = {".git", "node_modules", ".venv", "venv", "__pycache__", "dist", "build",
             ".pytest_cache", ".ruff_cache", ".mypy_cache"}


class UsageError(Exception):
    pass


def parse_rule_overrides(values: list[str]) -> dict[str, str]:
    severities: dict[str, str] = {}
    for value in values:
        for chunk in value.split(","):
            chunk = chunk.strip()
            if not chunk:
                continue
            if "=" not in chunk:
                raise UsageError(f"规则写法应为 CODE=off|warn|error|info：{chunk}")
            code, _, level = chunk.partition("=")
            code = code.strip().upper()
            level = level.strip().lower()
            if code not in RULES:
                raise UsageError(f"没有这条规则：{code}（用 --list-rules 看全部）")
            if level not in {"off", "warn", "error", "info"}:
                raise UsageError(f"严重度只能是 off/warn/error/info：{level}")
            severities[code] = level
    return severities


def load_ignore(cwd: Path) -> list[str]:
    patterns: list[str] = []
    current = cwd.resolve()
    for parent in [current, *current.parents]:
        candidate = parent / IGNORE_FILE
        if candidate.is_file():
            for line in candidate.read_text(encoding="utf-8-sig").splitlines():
                line = line.strip()
                if line and not line.startswith("#"):
                    patterns.append(line)
            break
    env = os.environ.get("ZH_PUNCT_IGNORE", "")
    patterns.extend(p for p in env.split(os.pathsep) if p)
    return patterns


def ignored(path: Path, patterns: list[str], root: Path) -> bool:
    try:
        relative = path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        relative = path.as_posix()
    for pattern in patterns:
        if fnmatch.fnmatch(relative, pattern) or fnmatch.fnmatch(path.name, pattern):
            return True
        if relative.startswith(pattern.rstrip("/") + "/"):
            return True
    return False


def iter_targets(paths: list[str], exts: set[str], patterns: list[str],
                 root: Path) -> list[Path]:
    found: list[Path] = []
    for raw in paths:
        path = Path(raw)
        if not path.exists():
            raise UsageError(f"找不到路径：{raw}")
        if path.is_dir():
            for child in sorted(path.rglob("*")):
                if child.is_dir() or any(part in SKIP_DIRS for part in child.parts):
                    continue
                if child.suffix.lower() in exts and not ignored(child, patterns, root):
                    found.append(child)
        elif not ignored(path, patterns, root):
            found.append(path)
    return found


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError as error:
        raise UsageError(f"{path} 不是 UTF-8：{error}") from error


def write_text(path: Path, text: str) -> None:
    newline = "\r\n" if b"\r\n" in path.read_bytes() else "\n"
    with path.open("w", encoding="utf-8", newline="") as handle:
        handle.write(text.replace("\r\n", "\n").replace("\n", newline))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="zh-punct",
        description="中文排版体检：全半角混用、成对符号不闭合、重复标点、省略号与破折号写法。",
    )
    parser.add_argument("paths", nargs="*", help="要检查的文件或目录，用 - 读 stdin")
    parser.add_argument("--fix", action="store_true", help="落盘修复安全规则")
    parser.add_argument("--rule", action="append", default=[], metavar="CODE=LEVEL",
                        help="改规则严重度，可逗号分隔，可重复")
    parser.add_argument("--format", default="text", choices=sorted(FORMATS),
                        help="输出格式，默认 text")
    parser.add_argument("--ignore", action="append", default=[], metavar="GLOB",
                        help="忽略匹配的文件，可重复")
    parser.add_argument("--ext", action="append", default=[], metavar=".md",
                        help="目录递归时只收这些后缀，可重复")
    parser.add_argument("--no-markdown", action="store_true",
                        help="按纯文本处理：不跳过代码块与行内代码")
    parser.add_argument("--list-rules", action="store_true", help="列出全部规则后退出")
    parser.add_argument("--version", action="version", version=f"zh-punct {__version__}")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.list_rules:
        for rule in RULES.values():
            fixable = "可自动修复" if rule.fixable else "只报不改"
            print(f"{rule.code}  {rule.severity:<5} {rule.title}（{fixable}）")
            print(f"      {rule.detail}")
        return 0

    if not args.paths:
        parser.print_help(sys.stderr)
        return 2

    try:
        severities = parse_rule_overrides(args.rule)
        exts = {e.lower() if e.startswith(".") else "." + e.lower() for e in args.ext}
        exts = exts or DEFAULT_EXTS
        root = Path.cwd()
        patterns = [*load_ignore(root), *args.ignore]
        markdown = not args.no_markdown

        if args.paths == ["-"]:
            targets: list[Path] = []
            stdin_text = sys.stdin.read()
        else:
            targets = iter_targets(args.paths, exts, patterns, root)
            stdin_text = ""

        if not targets and not stdin_text:
            print("zh-punct: 没有匹配到文件", file=sys.stderr)
            return 0

        all_found = []
        sources: dict[str, str] = {}
        for path in targets:
            text = read_text(path)
            found, _ = check_text(text, path.as_posix(), severities, markdown)
            sources[path.as_posix()] = text
            all_found.extend(found)

        if stdin_text:
            found, _ = check_text(stdin_text, "-", severities, markdown)
            all_found.extend(found)

        if args.fix:
            for path in targets:
                key = path.as_posix()
                original = sources[key]
                fixed = apply_fixes(original, [d for d in all_found if d.path == key], severities)
                if fixed != original:
                    write_text(path, fixed)
                    print(f"zh-punct: 已修复 {key}", file=sys.stderr)
            if stdin_text:
                sys.stdout.write(apply_fixes(stdin_text, all_found, severities))
            remaining: list = []
            for path in targets:
                text = read_text(path)
                again, _ = check_text(text, path.as_posix(), severities, markdown)
                remaining.extend(again)
            all_found = remaining
            if not targets:
                return 0

        if all_found:
            print(FORMATS[args.format](all_found))
            return 1
        return 0
    except UsageError as error:
        print(f"zh-punct: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
