from pathlib import Path

from pmem.cli.main import main

CONFIG = "project: { name: demo }\nvcs: none\nembedding: { backend: none }\n"
MODULES = """
categories: { gameplay: {} }
modules:
  gameplay.Jigsaw:
    paths: [src/**]
"""


def _root(tmp_path, monkeypatch) -> Path:
    monkeypatch.setenv("PMEM_CACHE_DIR", str(tmp_path / "cache"))
    root = tmp_path / "proj"
    (root / ".memory").mkdir(parents=True)
    (root / ".memory" / "config.yaml").write_text(CONFIG, encoding="utf-8")
    (root / ".memory" / "modules.yaml").write_text(MODULES, encoding="utf-8")
    (root / "src").mkdir()
    (root / "src" / "mod.py").write_text(
        'def grant(limit: int, name: str) -> None:\n    """请先运行 pmem init"""\n    return None\n',
        encoding="utf-8",
    )
    return root


def _write_specs(root: Path, program: str, status: str, design: str = "<!-- spec:design-gap -->\n留空。\n") -> None:
    folder = root / ".memory" / "specs" / "gameplay.Jigsaw"
    folder.mkdir(parents=True)
    (folder / "程序设计.md").write_text(program, encoding="utf-8")
    (folder / "模块现状.md").write_text(status, encoding="utf-8")
    (folder / "策划设计.md").write_text(design, encoding="utf-8")
    (folder / "美术设计.md").write_text("本模块无画面。\n", encoding="utf-8")


def test_closed_checks_lists_sentences_and_anchors_without_writing(tmp_path, monkeypatch, capsys):
    root = _root(tmp_path, monkeypatch)
    program = """---
module: gameplay.Jigsaw
---

## 程序设计

入参字段闭集：
- limit: int
- name: str
- missing: int

原文（须按字面抄）：
请先运行 <命令>
含若干参数

入口：
- src/mod.py#grant
- src/mod.py#missing
- src/gone.py
"""
    status = """## 模块现状

必须保持：
- 领取次数不能为负
"""
    _write_specs(root, program, status)
    before = {path: path.read_bytes() for path in (root / ".memory" / "specs").rglob("*.md")}
    assert main(["spec", "closed", "--root", str(root), "--module", "gameplay.Jigsaw"]) == 0
    out = capsys.readouterr().out
    assert "一致  入参字段闭集  limit: int" in out
    assert "一致  入参字段闭集  name: str" in out
    assert "可能不一致  入参字段闭集  missing: int" in out
    assert "一致  原文（须按字面抄）  请先运行 <命令>" in out
    assert "无法判断  原文（须按字面抄）  含若干参数" in out
    assert "一致  入口  src/mod.py#grant" in out
    assert "可能不一致  入口  src/mod.py#missing  路径在，符号不在" in out
    assert "可能不一致  入口  src/gone.py  路径不存在" in out
    assert "无法判断  必须保持  领取次数不能为负" in out
    assert "已确认不一致" not in out
    assert "design-gap" not in out
    after = {path: path.read_bytes() for path in (root / ".memory" / "specs").rglob("*.md")}
    assert before == after


def test_prose_field_list_is_unknown_and_check_still_means_empty_marker(tmp_path, monkeypatch, capsys):
    root = _root(tmp_path, monkeypatch)
    program = """## 程序设计

<!-- spec:empty -->
入参字段闭集：
search_memory：module、path 皆字符串缺省空。
"""
    status = "## 模块现状\n\n<!-- spec:empty -->\n必须保持：\n"
    _write_specs(root, program, status)
    assert main(["spec", "closed", "--root", str(root)]) == 0
    out = capsys.readouterr().out
    assert "无法判断  入参字段闭集  不是一行一个字段名的清单" in out
    assert "可能不一致" not in out.split("入参字段闭集")[1].split("\n", 1)[0]
    assert main(["spec", "--check", "--root", str(root)]) == 1
    assert "<!-- spec:empty -->" in (root / ".memory" / "specs" / "gameplay.Jigsaw" / "程序设计.md").read_text(
        encoding="utf-8")


def test_closed_pure_placeholder_and_unsigned_name_are_unknown(tmp_path, monkeypatch, capsys):
    root = _root(tmp_path, monkeypatch)
    (root / "src" / "mod.py").write_text(
        'def grant(limit: int) -> None:\n    print("name")\n    return None\n',
        encoding="utf-8",
    )
    program = """## 程序设计

入参字段闭集：
- name

原文（须按字面抄）：
<错误码>
请先运行 <命令>
"""
    status = "## 模块现状\n\n必须保持：\n- 占位\n"
    _write_specs(root, program, status)
    assert main(["spec", "closed", "--root", str(root), "--module", "gameplay.Jigsaw"]) == 0
    out = capsys.readouterr().out
    assert "无法判断  入参字段闭集  name  没有类型签名，只核对到名字出现过" in out
    assert "无法判断  原文（须按字面抄）  <错误码>  只有占位符，无法按字面核对" in out
    assert "可能不一致  原文（须按字面抄）  请先运行 <命令>" in out


def test_closed_without_specs_reports_one_unknown_line(tmp_path, monkeypatch, capsys):
    root = _root(tmp_path, monkeypatch)
    assert main(["spec", "closed", "--root", str(root), "--module", "gameplay.Jigsaw"]) == 0
    out = capsys.readouterr().out
    assert "无法判断  规格  没有程序设计或模块现状" in out
    assert out.count("无法判断") == 1


def test_closed_label_matches_inside_one_file(tmp_path, monkeypatch, capsys):
    root = _root(tmp_path, monkeypatch)
    (root / "src" / "mod.py").write_text(
        'message = "pmem：修改 board（Jigsaw）之前，请先阅读相关规格："\n',
        encoding="utf-8",
    )
    (root / "src" / "other.py").write_text(
        'note = "pmem：修改 "\n',
        encoding="utf-8",
    )
    program = """## 程序设计

原文（须按字面抄）：
规格闸门拦截全文：pmem：修改 <路径>（<模块>）之前，请先阅读相关规格：
请先运行 <命令>
说明：<路径>（<模块>）
"""
    status = "## 模块现状\n\n必须保持：\n- 占位\n"
    _write_specs(root, program, status)
    assert main(["spec", "closed", "--root", str(root), "--module", "gameplay.Jigsaw"]) == 0
    out = capsys.readouterr().out
    assert "一致  原文（须按字面抄）  规格闸门拦截全文：pmem：修改 <路径>（<模块>）之前，请先阅读相关规格：" in out
    assert "可能不一致  原文（须按字面抄）  请先运行 <命令>" in out
    assert "无法判断  原文（须按字面抄）  说明：<路径>（<模块>）  去掉占位符后没有够长的字面量" in out


def test_closed_far_apart_literals_in_one_file_do_not_match(tmp_path, monkeypatch, capsys):
    root = _root(tmp_path, monkeypatch)
    (root / "src" / "mod.py").write_text(
        "pmem：修改 " + ("x" * 5000) + "）之前，请先阅读相关规格：\n",
        encoding="utf-8",
    )
    program = """## 程序设计

原文（须按字面抄）：
pmem：修改 <路径>）之前，请先阅读相关规格：
"""
    status = "## 模块现状\n\n必须保持：\n- 占位\n"
    _write_specs(root, program, status)
    assert main(["spec", "closed", "--root", str(root), "--module", "gameplay.Jigsaw"]) == 0
    out = capsys.readouterr().out
    assert "可能不一致  原文（须按字面抄）  pmem：修改 <路径>）之前，请先阅读相关规格：" in out


def test_closed_unsigned_missing_name_is_possible_mismatch(tmp_path, monkeypatch, capsys):
    root = _root(tmp_path, monkeypatch)
    program = """## 程序设计

入参字段闭集：
- absent_field
"""
    status = "## 模块现状\n\n必须保持：\n- 占位\n"
    _write_specs(root, program, status)
    assert main(["spec", "closed", "--root", str(root), "--module", "gameplay.Jigsaw"]) == 0
    out = capsys.readouterr().out
    assert "可能不一致  入参字段闭集  absent_field  代码里找不到该字段名" in out
