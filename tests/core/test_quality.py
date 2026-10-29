from pmem.core.quality import content_hints, entity_hint, similar_entity_pairs


def test_conclusion_with_reason_has_no_hint():
    assert content_hints("根因：领取按钮没有防连点，断线重连时会调用两次。", 600) == []


def test_changelog_style_is_hinted():
    hints = content_hints("新增了领取记录表，调整了按钮状态。", 600)
    assert len(hints) == 1 and "变更记录" in hints[0]


def test_changelog_words_with_reason_are_fine():
    assert content_hints("修复重复发奖：原因是服务端没有按关卡做幂等校验。", 600) == []


def test_regression_and_known_issue_notes_count_as_reason():
    assert content_hints("生成布局改为底对齐。回归：单列与三列礼包界面。", 600) == []
    assert content_hints("紧急盘改为只校验摆放解。已知：紧急盘可多解。", 600) == []


def test_missing_reason_is_hinted():
    hints = content_hints("拼图界面在低端机上加载慢。", 600)
    assert len(hints) == 1 and "为什么" in hints[0]


def test_too_long_is_hinted():
    hints = content_hints("根因是缓存未清理。" + "细" * 700, 600)
    assert any("超过建议" in h for h in hints)


def test_exclusion_shaped_conclusion_or_decision_is_hinted():
    for kind, text in (
        ("conclusion", "排除：不要按采用率调检索排序，每人结果会不同。"),
        ("decision", "不要用时间排序，相关度低的老结论会被挤掉。"),
        ("conclusion", "决定：排除按相关度阈值过滤，真实分数会重叠。"),
    ):
        hints = content_hints(text, 600, kind)
        assert any("exclusion" in h for h in hints), (kind, text, hints)
    assert content_hints("根因：领取按钮没有防连点，断线重连时会调用两次。", 600, "conclusion") == []
    assert not any("exclusion" in h for h in content_hints("排除：客户端去重无效。", 600, "exclusion"))
    assert not any("exclusion" in h for h in content_hints("别人改了配置表字段名，对账对不上。", 600, "conclusion"))


def test_known_or_empty_entity_has_no_hint():
    assert entity_hint("Reward", ["reward", "Config"]) is None
    assert entity_hint("Reward", []) is None


def test_new_entity_lists_only_similar_existing_names():
    hint = entity_hint("RewardClaim", ["Config", "Reward", "Save", "Rewards"])
    assert hint is not None
    assert hint.split("已有：")[1].split("。")[0].split("、") == ["Reward", "Rewards"]


def test_unrelated_new_entity_is_not_hinted():
    assert entity_hint("Report", ["Events", "Compare", "Bench"]) is None


def test_short_contained_name_is_not_related():
    assert entity_hint("Level1Guide", ["UI"]) is None
    assert entity_hint("BannerLayout", ["Banner"]) is not None


def test_similar_entity_pairs_only_flags_likely_duplicates():
    names = ["Reward", "Rewards", "reward", "AutoPop", "AutoPopup", "Banner", "BannerLayout", "Analytics", "Animation"]
    assert similar_entity_pairs(names) == [("AutoPop", "AutoPopup"), ("Reward", "Rewards")]
