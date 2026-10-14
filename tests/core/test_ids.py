import time

from pmem.core.ids import ALPHABET, new_ulid
from pmem.index.store import ulid_ms


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


def test_explicit_past_time_is_kept_after_a_later_one():
    new_ulid(now_ms=1_900_000_000_000)
    assert ulid_ms(new_ulid(now_ms=1_700_000_000_000)) == 1_700_000_000_000
    assert abs(ulid_ms(new_ulid()) - time.time() * 1000) < 60_000
