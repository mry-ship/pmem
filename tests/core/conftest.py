import pytest
import yaml

from pmem.core.registry import ModuleRegistry

MODULES_YAML = """
schema_version: 1
categories:
  activity: { label: 限时运营活动 }
  gameplay: { label: 核心与常驻玩法 }
  economy:  { label: 货币与数值 }
  infra:    { label: 技术底座 }
entities:
  Config: [config, settings, 配置]
  Reward: [reward, 奖励]
modules:
  activity.ClimbBeanstalk:
    paths:
      - Assets/Runtime/General/ClimbBeanstalk/**
      - Assets/Runtime/General/ClimbBeanstalkLevel/**
      - Assets/Game/ClimbBeanstalk_*/**
    aliases: [ClimbBeanstalkLevel]
    entities: [Schedule, Level]
  gameplay.Jigsaw:
    paths: [Assets/Jigsaw/**]
    aliases: [Puzzle, activity.Jigsaw]
  gameplay.JigsawOld:
    status: merged_into:gameplay.Jigsaw
  economy.Shop:
    paths: [Assets/Runtime/General/Shop/**, Assets/UI/ShopPanel/**]
  infra.Framework:
    paths: [Assets/Framework/**]
    components: [DataNode, ObjectPool]
  infra.Common:
    paths: [Assets/Framework/Common/**]
candidates:
  activity.Ladybug:
    paths: [Assets/Runtime/General/Ladybug/**]
third_party:
  - Assets/GoogleMobileAds/**
ignored:
  - { path: Assets/Demo, reason: 示例代码 }
"""


@pytest.fixture
def registry() -> ModuleRegistry:
    return ModuleRegistry(yaml.safe_load(MODULES_YAML))
