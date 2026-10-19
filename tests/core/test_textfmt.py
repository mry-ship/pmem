from pmem.core.textfmt import format_content

LONG = ("入口一会出现一会消失。窗口只由整轮通关触发，当日结束后关闭，同日只开一次，跨天会话直接清空并隐藏入口。"
        "高概率原因：1) 设计上非常驻；2) 结算期间刷新会先藏再显；3) 跨自然日清会话。回归：领奖前后入口应稳定。")


def test_long_lines_break_at_sentences_and_inline_numbering():
    assert format_content(LONG, width=40).splitlines() == [
        "入口一会出现一会消失。",
        "窗口只由整轮通关触发，当日结束后关闭，同日只开一次，跨天会话直接清空并隐藏入口。",
        "高概率原因：",
        "  1) 设计上非常驻；",
        "  2) 结算期间刷新会先藏再显；",
        "  3) 跨自然日清会话。",
        "回归：领奖前后入口应稳定。",
    ]


def test_only_line_breaks_change_and_result_is_stable():
    once = format_content(LONG, width=40)
    assert "".join(once.split()) == "".join(LONG.split())
    assert format_content(once, width=40) == once


def test_short_lines_code_blocks_and_tables_are_untouched():
    code = "x = 1。" * 30
    text = f"短行。不用断。\n\n```\n{code}\n```\n| 列 | {'很长。' * 40} |"
    assert format_content(text) == text


def test_does_not_break_inside_brackets():
    text = "检索不受影响（换行只是空白；句号本来就打断二元组）。" + "后面还有一句很长的说明。" * 3
    assert format_content(text, width=30).splitlines()[0] == "检索不受影响（换行只是空白；句号本来就打断二元组）。"
    assert format_content("检索不受影响（换行只是空白；\n句号本来就打断二元组）。") == "检索不受影响（换行只是空白；句号本来就打断二元组）。"


def test_unbalanced_bracket_does_not_swallow_following_lines():
    text = "取值区间为 (0, 1]，超出会被截断。\n原因：配置没校验。\n风险：旧存档里的 0 值 :( 会报错。"
    assert format_content(text) == text


def test_list_items_keep_continuation_indent():
    item = "- " + "第一句说明根因在服务端校验。" * 5 + "第二句说明影响范围。"
    lines = format_content(item).splitlines()
    assert lines[0].startswith("- 第一句") and all(line.startswith("  ") for line in lines[1:])
