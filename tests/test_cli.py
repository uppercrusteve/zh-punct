"""CLI 行为：退出码、修复、格式、忽略、配置。"""

import json
import subprocess
import sys
from pathlib import Path

from zh_punct.cli import main
from zh_punct.rules import Diagnostic, apply_fixes


def run(tmp_path: Path, *argv: str) -> int:
    return main([*argv])


def write(tmp_path: Path, name: str, text: str) -> Path:
    path = tmp_path / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def test_clean_file_exit_zero(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    path = write(tmp_path, "a.md", "你好，世界。\n")
    assert run(tmp_path, str(path)) == 0


def test_finding_exit_one(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    path = write(tmp_path, "a.md", "你好,世界\n")
    assert run(tmp_path, str(path)) == 1


def test_missing_path_exit_two(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    assert run(tmp_path, "nope.md") == 2


def test_bad_rule_name_exit_two(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    path = write(tmp_path, "a.md", "你好,世界\n")
    assert run(tmp_path, str(path), "--rule", "ZP999=off") == 2


def test_fix_rewrites_file(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    path = write(tmp_path, "a.md", "你好,世界...\n")
    assert run(tmp_path, str(path), "--fix") == 0
    assert path.read_text(encoding="utf-8") == "你好，世界……\n"


def test_fix_keeps_crlf(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    path = tmp_path / "a.md"
    path.write_bytes("你好,世界\r\n".encode())
    run(tmp_path, str(path), "--fix")
    assert path.read_bytes() == "你好，世界\r\n".encode()


def test_fix_leaves_unfixable(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    path = write(tmp_path, "a.md", "他说“走, 好\n")
    assert run(tmp_path, str(path), "--fix") == 1
    assert path.read_text(encoding="utf-8") == "他说“走， 好\n"


def test_fix_respects_disabled_rule(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    path = write(tmp_path, "a.md", "你好,世界\n")
    run(tmp_path, str(path), "--fix", "--rule", "ZP001=off")
    assert path.read_text(encoding="utf-8") == "你好,世界\n"


def test_json_format(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    path = write(tmp_path, "a.md", "你好,世界\n")
    run(tmp_path, str(path), "--format", "json")
    payload = json.loads(capsys.readouterr().out)
    assert payload[0]["code"] == "ZP001"
    assert payload[0]["line"] == 1


def test_github_format(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    path = write(tmp_path, "a.md", "你好,世界\n")
    run(tmp_path, str(path), "--format", "github")
    assert "::error file=" in capsys.readouterr().out


def test_directory_recursion(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    write(tmp_path, "docs/a.md", "你好,世界\n")
    assert run(tmp_path, "docs") == 1


def test_directory_skips_node_modules(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    write(tmp_path, "node_modules/x/a.md", "你好,世界\n")
    assert run(tmp_path, ".") == 0


def test_ignore_file(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    write(tmp_path, ".zhpunctignore", "draft/**\n")
    write(tmp_path, "draft/a.md", "你好,世界\n")
    assert run(tmp_path, ".") == 0


def test_ignore_flag(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    path = write(tmp_path, "a.md", "你好,世界\n")
    assert run(tmp_path, str(path), "--ignore", "a.md") == 0


def test_list_rules_exit_zero(capsys):
    assert main(["--list-rules"]) == 0
    assert "ZP001" in capsys.readouterr().out


def test_stdin(capsys, monkeypatch):
    import io
    monkeypatch.setattr(sys, "stdin", io.StringIO("你好,世界\n"))
    assert main(["-"]) == 1


def test_apply_fixes_skips_overlap():
    text = "好，，坏"
    diagnostics = [
        Diagnostic("t.md", 1, 2, "ZP005", "error", "", (1, 3, "，")),
        Diagnostic("t.md", 1, 3, "ZP005", "error", "", (2, 3, "，")),
    ]
    assert apply_fixes(text, diagnostics, {}) == "好，坏"


def test_module_entrypoint(tmp_path):
    path = tmp_path / "a.md"
    path.write_text("你好,世界\n", encoding="utf-8")
    result = subprocess.run(
        [sys.executable, "-m", "zh_punct.cli", str(path)],
        capture_output=True, text=True, encoding="utf-8", check=False,
        env={"PYTHONPATH": str(Path(__file__).resolve().parents[1] / "src"),
             "PYTHONUTF8": "1", "PATH": ""},
    )
    assert result.returncode == 1
    assert "ZP001" in result.stdout


def test_example_fix_matches_expected(tmp_path, monkeypatch, capsys):
    root = Path(__file__).resolve().parents[1]
    source = (root / "examples/before.md").read_text(encoding="utf-8")
    path = tmp_path / "before.md"
    path.write_text(source, encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    run(tmp_path, str(path), "--fix")
    assert path.read_text(encoding="utf-8") == (root / "examples/after.md").read_text(
        encoding="utf-8")
