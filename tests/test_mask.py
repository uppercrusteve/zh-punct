"""掩码层：代码块、行内代码、front matter、控制注释。"""

from zh_punct.rules import check_text


def codes(text: str) -> list[str]:
    return [d.code for d in check_text(text, "t.md")[0]]


def test_fenced_code_block_skipped():
    assert codes("```\n你好,世界\n```") == []


def test_tilde_fence_skipped():
    assert codes("~~~\n你好,世界\n~~~") == []


def test_indented_code_block_skipped():
    assert codes("段落\n\n    你好,世界\n") == []


def test_inline_code_skipped():
    assert codes("用 `a,b` 分隔") == []


def test_double_backtick_span_skipped():
    assert codes("用 ``a,b`` 分隔") == []


def test_front_matter_skipped():
    assert codes("---\ntitle: a,b\n---\n\n正文。") == []


def test_html_comment_skipped():
    assert codes("<!-- 你好,世界 -->\n正文。") == []


def test_region_off_on():
    text = "<!-- zh-punct: off -->\n你好,世界\n<!-- zh-punct: on -->\n坏,好"
    found = check_text(text, "t.md")[0]
    assert len(found) == 1
    assert found[0].line == 4


def test_line_skip_line():
    assert codes("你好,世界 <!-- zh-punct: skip-line -->") == []


def test_skip_line_only_affects_its_line():
    text = "你好,世界 <!-- zh-punct: skip-line -->\n坏,好"
    assert codes(text) == ["ZP001"]


def test_reference_definition_destination_skipped():
    assert codes("[文档]: https://a.com/a(b)\n\n正文。") == []


def test_link_destination_skipped():
    assert codes("见[说明](docs/a(b).md)一节。") == []


def test_markdown_off_checks_code_blocks():
    found = check_text("```\n你好,世界\n```", "t.txt", markdown=False)[0]
    assert [d.code for d in found] == ["ZP001"]


def test_empty_document():
    assert codes("") == []


def test_crlf_columns_stay_aligned():
    found = check_text("第一行\r\n你好,世界\r\n", "t.md")[0]
    assert (found[0].line, found[0].col) == (2, 3)
