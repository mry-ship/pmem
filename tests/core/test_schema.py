import pytest

from pmem.core.schema import (
    SchemaError,
    expect_bool,
    expect_list,
    expect_mapping,
    expect_number,
    expect_one_of,
    expect_str,
)


def test_expect_mapping_and_list_coercion():
    assert expect_mapping({"a": 1}, "root") == {"a": 1}
    assert expect_list(["x"], "paths") == ["x"]
    assert expect_list("solo", "paths") == ["solo"]
    with pytest.raises(SchemaError, match="应是键值对"):
        expect_mapping([], "root")
    with pytest.raises(SchemaError, match="应是列表"):
        expect_list(3, "paths")


def test_expect_scalars_and_one_of():
    assert expect_str("block", "gate.mode") == "block"
    assert expect_bool(True, "flag") is True
    assert expect_number(5, "limit", minimum=1) == 5.0
    assert expect_one_of("warn", "gate.mode", ("warn", "block", "off")) == "warn"
    with pytest.raises(SchemaError, match="应 ≥ 1"):
        expect_number(0, "limit", minimum=1)
    with pytest.raises(SchemaError, match="之一"):
        expect_one_of("blok", "gate.mode", ("warn", "block", "off"))
