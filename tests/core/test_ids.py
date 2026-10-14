from pmem.core.ids import ALPHABET, new_ulid


def test_ulid_has_26_crockford_chars():
    value = new_ulid()
    assert len(value) == 26
    assert set(value) <= set(ALPHABET)


def test_ulids_are_unique_and_sorted_in_creation_order():
    values = [new_ulid() for _ in range(2000)]
    assert len(set(values)) == len(values)
    assert values == sorted(values)


def test_later_millisecond_sorts_after():
    first = new_ulid(now_ms=1_900_000_000_000)
    second = new_ulid(now_ms=1_900_000_000_001)
    assert second > first
