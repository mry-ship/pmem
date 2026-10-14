from pmem.index.tokenize import tokenize


def test_chinese_becomes_bigrams():
    assert tokenize("奖励重复") == ["奖励", "励重", "重复"]


def test_single_chinese_char_is_kept():
    assert tokenize("奖") == ["奖"]


def test_ascii_words_are_lowercased_and_split_on_case():
    assert tokenize("GrantReward retry_count") == ["grantreward", "grant", "reward", "retry_count", "retry", "count"]


def test_mixed_text():
    tokens = tokenize("Jigsaw奖励 v2")
    assert "jigsaw" in tokens
    assert "奖励" in tokens
    assert "v2" in tokens
