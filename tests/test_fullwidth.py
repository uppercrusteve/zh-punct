"""ZP001 / ZP002：全半角标点。"""

from zh_punct.rules import check_text


def codes(text: str) -> list[str]:
    return [d.code for d in check_text(text, "t.md")[0]]


def test_comma_between_han_characters():
    found = check_text("你好,世界", "t.md")[0]
    assert [d.code for d in found] == ["ZP001"]
    assert found[0].col == 3


def test_comma_after_percent_still_counted():
    assert "ZP001" in codes("增长12%, 下降")


def test_halfwidth_brackets_around_han():
    assert codes("英文(括号)").count("ZP001") == 2


def test_full_stop_between_han():
    found = check_text("你好.开始", "t.md")[0]
    assert found[0].fix == (2, 3, "。")


def test_question_and_exclamation():
    assert codes("走吗?走!") == ["ZP001", "ZP001"]


def test_decimal_point_untouched():
    assert codes("总量3.14吨") == []


def test_thousands_separator_untouched():
    assert codes("共1,000人") == []


def test_version_number_untouched():
    assert codes("版本v0.1.0，已发布") == []


def test_ascii_parens_in_han_line_untouched():
    assert codes("跑 foo(bar) 看看") == []


def test_ascii_parens_with_han_inside_are_flagged():
    assert codes("打开 docs/methods.md(见说明)") == ["ZP001", "ZP001"]


def test_comma_after_url_is_flagged():
    assert codes("见 https://example.com/a，再看") == []


def test_halfwidth_comma_after_url_is_flagged():
    assert codes("见 https://a.com/x?y=1, 后面还有") == ["ZP001"]


def test_html_tag_untouched():
    assert codes('<a href="x" title="a,b">链接</a>') == []


def test_escaped_comma_untouched():
    assert codes(r"你好\,世界") == []


def test_pure_english_line_untouched():
    assert codes("Hello, world. It works!") == []


def test_fullwidth_punct_in_english_line():
    assert codes("Hello，world") == ["ZP002"]


def test_fullwidth_punct_in_han_line_not_flagged_as_zp002():
    assert "ZP002" not in codes("你好，世界")


def test_reference_line_comma_exempt():
    assert codes("| [28] | 翁伯琦, 王义祥, 应朝阳, 等. 果园生草栽培. 学报, 2020 |") == []


def test_bare_reference_line_exempt():
    assert codes("[12] 张三, 李四. 题目. 期刊, 2021, 3(2): 1-9.") == []


def test_non_reference_line_still_checked():
    assert codes("名单：张三, 李四都来了") == ["ZP001"]


def test_subscript_formula_in_parens_exempt():
    assert codes("把“(NaPO₃)₆”写对") == []


def test_reference_line_ellipsis_exempt():
    assert codes("| [46] | Reta B H, et al. Canopy management: A review... 园艺学报, 2025 |") == []


def test_single_latin_token_with_han_period():
    assert codes("MIT。") == []


def test_latin_sentence_with_han_period_still_flagged():
    assert codes("Hello world。") == ["ZP002"]
