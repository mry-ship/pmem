import pytest

from pmem.core.registry import RegistryError


def test_known_module_resolves_case_insensitively(registry):
    resolved = registry.resolve_module("GAMEPLAY.jigsaw")
    assert resolved.id == "gameplay.Jigsaw"
    assert resolved.known is True


def test_full_alias_resolves_to_target(registry):
    assert registry.resolve_module("activity.Jigsaw").id == "gameplay.Jigsaw"


def test_bare_alias_resolves_to_target(registry):
    assert registry.resolve_module("Puzzle").id == "gameplay.Jigsaw"


def test_bare_module_name_resolves_when_unique(registry):
    assert registry.resolve_module("shop").id == "economy.Shop"


def test_merged_module_redirects(registry):
    resolved = registry.resolve_module("gameplay.JigsawOld")
    assert resolved.id == "gameplay.Jigsaw"
    assert resolved.redirected_from == "gameplay.JigsawOld"


def test_unknown_module_in_known_category_is_allowed(registry):
    resolved = registry.resolve_module("activity.WorldCup")
    assert resolved.id == "activity.WorldCup"
    assert resolved.known is False


def test_candidate_module_is_reported_as_candidate(registry):
    resolved = registry.resolve_module("activity.ladybug")
    assert resolved.id == "activity.Ladybug"
    assert resolved.known is False
    assert resolved.candidate is True


def test_unknown_category_is_rejected_with_allowed_list(registry):
    with pytest.raises(RegistryError, match="activity / gameplay / economy / infra"):
        registry.resolve_module("ui.Button")


def test_malformed_name_is_rejected(registry):
    with pytest.raises(RegistryError):
        registry.resolve_module("activity.Bad Name")


def test_unknown_bare_name_is_rejected(registry):
    with pytest.raises(RegistryError, match="category.Name"):
        registry.resolve_module("Nothing")


def test_entity_alias_resolves_to_canonical(registry):
    assert registry.resolve_entity("gameplay.Jigsaw", "配置") == "Config"
    assert registry.resolve_entity("gameplay.Jigsaw", "REWARD") == "Reward"


def test_module_entity_and_component_resolve_case_insensitively(registry):
    assert registry.resolve_entity("activity.ClimbBeanstalk", "schedule") == "Schedule"
    assert registry.resolve_entity("infra.Framework", "objectpool") == "ObjectPool"


def test_unknown_entity_is_kept_as_given(registry):
    assert registry.resolve_entity("gameplay.Jigsaw", " Exp89 ") == "Exp89"
