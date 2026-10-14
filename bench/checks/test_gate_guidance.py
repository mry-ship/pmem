"""隐藏验收：闸门拦截时，Agent 实际能看到的文字里要写明下一步该调用什么。"""
from pmem.hooks.gate import handle

ENTRY = """---
id: 01JA7K3M2X9F4Q8W6ZB1C2D3E4
module: gameplay.Jigsaw
entity: Reward
kind: conclusion
status: active
author: a
note_date: '2026-10-01'
---
旧结论
"""


def test_deny_tells_agent_what_to_call(tmp_path, monkeypatch):
    monkeypatch.setenv("PMEM_CACHE_DIR", str(tmp_path / "cache"))
    root = tmp_path / "proj"
    (root / ".memory" / "entries" / "gameplay.Jigsaw").mkdir(parents=True)
    (root / ".memory" / "config.yaml").write_text("project: { name: demo }\nvcs: none\ngate: { mode: warn }\n", "utf-8")
    (root / ".memory" / "modules.yaml").write_text(
        "categories: { gameplay: {} }\nmodules:\n  gameplay.Jigsaw: { paths: [src/Jigsaw/**] }\n", "utf-8"
    )
    (root / ".memory" / "entries" / "gameplay.Jigsaw" / "01JA7K3M2X9F4Q8W6ZB1C2D3E4.md").write_text(ENTRY, "utf-8")
    payload = {"conversation_id": "c1", "tool_name": "Write",
               "tool_input": {"file_path": str(root / "src/Jigsaw/Board.cs"), "content": "x"}}
    verdict = handle("pre-tool", payload, root)
    assert verdict["permission"] == "deny"
    assert 'search_memory(module="gameplay.Jigsaw")' in verdict["user_message"]
