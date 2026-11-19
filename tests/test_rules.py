"""ZP004–ZP010：配对、重复、省略号、破折号、避头尾、波浪线、空格。"""

from __future__ import annotations

from zh_punct.rules import check_text


def codes(text: str, severities: dict[str, str] | None = None) -> list[str]:
    return [d.code for d in check_text(text, "t.md", severities)[0]]


def test_unclosed_quote():
    assert codes("他说“走吧") == ["ZP004"]


def test_surplus_closing_quote():
    assert codes("他说”走吧") == ["ZP004"]


def test_balanced_pairs_clean():
    assert codes("“引号”与（括号）与《书名》都闭合") == []


def test_pair_across_lines():
    assert codes("他说“今天\n先不走”") == []


def test_pair_inside_code_block_not_counted():
    assert codes("正文。\n\n```\n说「你好」\n```") == []


def test_quote_opened_in_prose_closed_in_code_block_still_reports():
    assert codes("他说“开\n\n```\n”\n```") == ["ZP004"]


def test_repeated_comma():
    assert codes("好，，坏") == ["ZP005"]


def test_repeated_exclamation():
    found = check_text("走！！", "t.md")[0]
    assert found[0].fix == (1, 3, "！")


def test_double_ellipsis_untouched():
    assert codes("等等……") == []


def test_ascii_dots_as_ellipsis():
    found = check_text("等等...", "t.md")[0]
    assert found[0].code == "ZP006"
    assert found[0].fix == (2, 5, "……")


def test_cjk_dots_as_ellipsis():
    assert codes("等等。。。") == ["ZP006"]


def test_single_ellipsis_char():
    assert codes("等等…再看") == ["ZP006"]


def test_ellipsis_in_english_line_untouched():
    assert codes("Wait...") == []


def test_double_hyphen_as_dash():
    found = check_text("甲--乙", "t.md")[0]
    assert found[0].code == "ZP007"
    assert found[0].fix == (1, 3, "——")


def test_real_dash_untouched():
    assert codes("甲——乙") == []


def test_table_separator_untouched():
    assert codes("| 名称 | 数量 |\n| --- | --- |\n| 好 | 1 |") == []


def test_punct_at_line_start():
    found = check_text("第一行\n，第二行", "t.md")[0]
    assert found[0].code == "ZP009"
    assert found[0].line == 2


def test_closing_quote_at_line_start():
    assert "ZP009" in codes("引文“半句\n”")


def test_punct_after_blank_line_not_flagged():
    assert codes("第一段\n\n，第二段") == []


def test_halfwidth_tilde_between_numbers_when_enabled():
    assert codes("1~2米", {"ZP010": "warn"}) == ["ZP010"]


def test_halfwidth_tilde_off_by_default():
    assert codes("1~2米") == []


def test_fullwidth_tilde_untouched():
    assert codes("1～2米", {"ZP010": "warn"}) == []


def test_spacing_off_by_default():
    assert codes("共3吨") == []


def test_spacing_when_enabled():
    assert codes("共3吨", {"ZP003": "warn"}) == ["ZP003"]


def test_spacing_fix_inserts_after_ascii():
    text = "共3吨"
    found = check_text(text, "t.md", {"ZP003": "warn"})[0]
    start, end, value = found[0].fix
    assert text[:start] + value + text[end:] == "共 3吨"


def test_spacing_ignores_punct():
    assert codes("共3吨，", {"ZP003": "warn"}) == ["ZP003"]


def test_disabled_rule_reports_nothing():
    assert codes("你好,世界", {"ZP001": "off"}) == []


def test_rule_severity_override():
    found = check_text("你好,世界", "t.md", {"ZP001": "info"})[0]
    assert found[0].severity == "info"
