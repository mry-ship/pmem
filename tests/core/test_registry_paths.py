import pytest
import yaml

from pmem.core.registry import ModuleRegistry, RegistryError, glob_specificity


def test_specific_feature_path_wins_over_umbrella(registry):
    match = registry.module_for_path("Assets/Framework/Common/Util.cs")
    assert match.module_id == "infra.Common"


def test_umbrella_catches_other_components(registry):
    assert registry.module_for_path("Assets/Framework/DataNode/Node.cs").module_id == "infra.Framework"


def test_module_owns_multiple_paths(registry):
    assert registry.module_for_path("Assets/Game/ClimbBeanstalk_Halloween/A.cs").module_id == "activity.ClimbBeanstalk"
    assert registry.module_for_path("Assets/Runtime/General/ClimbBeanstalkLevel/B.cs").module_id == "activity.ClimbBeanstalk"


def test_windows_separators_are_normalised(registry):
    assert registry.module_for_path("Assets\\UI\\ShopPanel\\Shop.cs").module_id == "economy.Shop"


def test_leading_dot_directory_is_kept(registry):
    assert registry.module_for_path(".memory/entries/x.md") is None
    assert registry.module_for_path("./Assets/Jigsaw/J.cs").module_id == "gameplay.Jigsaw"


def test_candidate_path_is_reported_as_candidate(registry):
    match = registry.module_for_path("Assets/Runtime/General/Ladybug/L.cs")
    assert match.module_id == "activity.Ladybug"
    assert match.candidate is True


def test_third_party_and_ignored_paths_map_to_nothing(registry):
    assert registry.module_for_path("Assets/GoogleMobileAds/Api/Ad.cs") is None
    assert registry.module_for_path("Assets/Demo/Sample.cs") is None


def test_unmapped_path_maps_to_nothing(registry):
    assert registry.module_for_path("Assets/Unknown/X.cs") is None


def test_equally_specific_conflict_raises():
    reg = ModuleRegistry(yaml.safe_load("""
categories: { infra: {}, gameplay: {} }
modules:
  infra.A: { paths: [Assets/Shared/**] }
  gameplay.B: { paths: [Assets/Shared/**] }
"""))
    with pytest.raises(RegistryError, match="infra.A"):
        reg.module_for_path("Assets/Shared/x.cs")


def test_specificity_prefers_more_literal_characters():
    assert glob_specificity("Assets/Framework/Common/**") > glob_specificity("Assets/Framework/**")
    assert glob_specificity("Assets/Game/ClimbBeanstalk_*/**") > glob_specificity("Assets/Game/**")
