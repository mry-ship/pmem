import json

from pmem.cli.anchors_cmd import FileIndex, find_anchors
from pmem.cli.main import main
from pmem.core.registry import ModuleRegistry

REGISTRY = ModuleRegistry({
    "modules": {
        "gameplay.Jigsaw": {"paths": ["src/Jigsaw/**"]},
        "economy.Shop": {"paths": ["src/Shop/**"]},
    },
    "third_party": ["src/Sdk/**"],
})


def write(root, rel, text="") -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_resolves_unique_files_and_class_members(tmp_path):
    write(tmp_path, "src/Jigsaw/RewardPanel.cs", "class RewardPanel { void OnClaim() {} }")
    write(tmp_path, "src/Jigsaw/Config.json", "{}")
    write(tmp_path, "src/Shop/Config.json", "{}")
    write(tmp_path, "src/Sdk/AdSdk.cs", "class AdSdk { void Show() {} }")
    files = FileIndex(tmp_path, REGISTRY)
    content = "RewardPanel.OnClaim 里重复发奖；Config.json 字段缺失；RewardPanel.Missing 已删；AdSdk.Show 是第三方"
    anchors = find_anchors(content, "gameplay.Jigsaw", files)
    assert anchors == ["src/Jigsaw/Config.json", "src/Jigsaw/RewardPanel.cs#OnClaim"]
    assert find_anchors("Config.json 字段缺失", "infra.Common", files) == []


def test_skips_vendor_directories_without_registry(tmp_path):
    write(tmp_path, "Assets/Plugins/UI/Menu.cs", "class Menu { void Close() {} }")
    write(tmp_path, "Assets/com.unity.ui/Runtime/Pager.cs", "class Pager { void Next() {} }")
    write(tmp_path, "Assets/Game/Shop.cs", "class Shop { void Buy() {} }")
    files = FileIndex(tmp_path, ModuleRegistry({}))
    assert find_anchors("Menu.Close、Pager.Next 与 Shop.Buy", "gameplay.Shop", files) == ["Assets/Game/Shop.cs#Buy"]


def test_cli_previews_then_applies(tmp_path, capsys, monkeypatch):
    monkeypatch.setenv("PMEM_CACHE_DIR", str(tmp_path / "cache"))
    monkeypatch.setenv("PMEM_AUTHOR", "alice")
    main(["init", "--root", str(tmp_path), "--type", "generic"])
    (tmp_path / ".memory" / "config.yaml").write_text("vcs: none\nembedding: { backend: none }\n", encoding="utf-8")
    write(tmp_path, "src/Login/TokenStore.ts", "export class TokenStore { refresh() {} }")
    capsys.readouterr()
    main(["record", "--root", str(tmp_path), "--module", "feature.Login", "--entity", "Token", "--kind",
          "conclusion", "--content", "TokenStore.refresh 失败时要清空缓存，避免死循环重试。"])
    written = json.loads(capsys.readouterr().out)

    assert main(["anchors", "--root", str(tmp_path)]) == 0
    assert "src/Login/TokenStore.ts#refresh" in capsys.readouterr().out
    path = next((tmp_path / ".memory" / "entries").rglob(f"{written['id']}.md"))
    assert "TokenStore.ts" not in path.read_text(encoding="utf-8")
    main(["anchors", "--root", str(tmp_path), "--apply"])
    assert "src/Login/TokenStore.ts#refresh" in path.read_text(encoding="utf-8")


def test_terms_and_graph_commands(tmp_path, capsys, monkeypatch):
    monkeypatch.setenv("PMEM_CACHE_DIR", str(tmp_path / "cache"))
    monkeypatch.setenv("PMEM_AUTHOR", "alice")
    main(["init", "--root", str(tmp_path), "--type", "generic"])
    (tmp_path / ".memory" / "config.yaml").write_text("vcs: none\nembedding: { backend: none }\n", encoding="utf-8")
    for text in ("进入登录页崩溃，原因是令牌为空，需要先判空。", "登录后偶发崩溃，原因是回调不在主线程执行。"):
        main(["record", "--root", str(tmp_path), "--module", "feature.Login", "--entity", "Crash", "--kind",
              "conclusion", "--content", text, "--alias", "闪退"])
    capsys.readouterr()
    main(["terms", "--root", str(tmp_path)])
    terms = {t["term"]: t["memories"] for t in json.loads(capsys.readouterr().out)["terms"]}
    assert terms["崩溃"] == 2 and terms["闪退"] == 2
    assert main(["graph", "--root", str(tmp_path), "--module", "feature.Login", "--entity", "crash"]) == 0
    assert len(json.loads(capsys.readouterr().out)["timeline"]) == 2
