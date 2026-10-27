import shutil
from pathlib import Path

import pytest

from pmem.cli.main import main

CONFIG = "project: { name: demo }\nvcs: none\nembedding: { backend: none }\n"
MODULES = """
categories: { gameplay: {}, legacy: {} }
modules:
  gameplay.Jigsaw:
    paths: [src/Jigsaw/**]
  gameplay.Jigsaw.Board:
    paths: [src/Jigsaw/Board/**]
  legacy.Old:
    paths: [src/Old/**]
    status: deprecated
"""


@pytest.fixture
def root(tmp_path, monkeypatch) -> Path:
    monkeypatch.setenv("PMEM_CACHE_DIR", str(tmp_path / "cache"))
    root = tmp_path / "proj"
    (root / ".memory").mkdir(parents=True)
    (root / ".memory" / "config.yaml").write_text(CONFIG, encoding="utf-8")
    (root / ".memory" / "modules.yaml").write_text(MODULES, encoding="utf-8")
    return root


def _folder(root: Path, module_id: str) -> Path:
    return root / ".memory" / "specs" / module_id


def test_init_writes_a_directory_of_four_files(root):
    assert main(["spec", "init", "--root", str(root)]) == 0
    folder = _folder(root, "gameplay.Jigsaw")
    art = (folder / "美术设计.md").read_text(encoding="utf-8")
    program = (folder / "程序设计.md").read_text(encoding="utf-8")
    status = (folder / "模块现状.md").read_text(encoding="utf-8")
    index = (folder / "index.md").read_text(encoding="utf-8")
    assert "<!-- spec:facts:start -->" in index and "src/Jigsaw/**" in index
    assert "gameplay.Jigsaw.Board" in index
    assert "src/Jigsaw" not in art
    assert "本模块无画面" in art and "<!-- spec:design-gap -->" in art
    assert "<!-- spec:empty -->" not in art
    assert program.count("<!-- spec:empty -->") == 1
    assert status.count("<!-- spec:empty -->") == 1
    assert "入口：" in program and "入参字段闭集" in program and "出参字段闭集" in program
    assert "生成物：" in program and "闭集词表" in program
    assert "失败条件：" in program and "配置与环境变量：" in program
    assert "所有权：" in program and "原文（须按字面抄）" in program
    assert "一轮例子：" in status and "依赖规格" in status
    assert "上级：gameplay.Jigsaw" in (_folder(root, "gameplay.Jigsaw.Board") / "index.md").read_text(encoding="utf-8")
    assert not (root / ".memory" / "specs" / ".gitignore").exists()


def test_init_again_keeps_part_bytes_and_fills_missing(root):
    assert main(["spec", "init", "--root", str(root)]) == 0
    program = _folder(root, "gameplay.Jigsaw") / "程序设计.md"
    program.write_text(program.read_text(encoding="utf-8").replace(
        "<!-- spec:empty -->", "<!-- spec:empty -->\n手写的程序细节", 1), encoding="utf-8")
    kept = program.read_text(encoding="utf-8")
    shutil.rmtree(_folder(root, "gameplay.Jigsaw.Board"))
    assert main(["spec", "init", "--root", str(root)]) == 0
    assert program.read_text(encoding="utf-8") == kept
    assert (_folder(root, "gameplay.Jigsaw.Board") / "程序设计.md").is_file()


def test_index_refreshes_facts_only(root):
    assert main(["spec", "init", "--root", str(root)]) == 0
    program = _folder(root, "gameplay.Jigsaw") / "程序设计.md"
    program.write_text(program.read_text(encoding="utf-8").replace("<!-- spec:empty -->", "已写完的程序\n", 1),
                       encoding="utf-8")
    kept = program.read_text(encoding="utf-8")
    modules = (root / ".memory" / "modules.yaml").read_text(encoding="utf-8")
    (root / ".memory" / "modules.yaml").write_text(
        modules.replace("src/Jigsaw/**", "src/Jigsaw/**, src/New/**"), encoding="utf-8")
    assert main(["spec", "index", "--root", str(root)]) == 0
    assert program.read_text(encoding="utf-8") == kept
    index = (_folder(root, "gameplay.Jigsaw") / "index.md").read_text(encoding="utf-8")
    assert "src/New/**" in index
    assert "已写完的程序" not in index
    catalog = (root / ".memory" / "specs" / "index.md").read_text(encoding="utf-8")
    assert "gameplay.Jigsaw.Board" in catalog
    assert "└ " in catalog
    assert "不要求补" in catalog


def test_dir_outside_project_is_refused(root):
    (root / ".memory" / "config.yaml").write_text(CONFIG + "spec: { dir: ../outside-specs }\n", encoding="utf-8")
    assert main(["spec", "init", "--root", str(root)]) == 2
    assert not (root.parent / "outside-specs").exists()


def test_symlink_page_is_not_overwritten(root):
    specs = root / ".memory" / "specs"
    specs.mkdir()
    sentinel = root / "AGENTS.md"
    sentinel.write_text("keep\n", encoding="utf-8")
    link = specs / "gameplay.Jigsaw"
    try:
        link.symlink_to(sentinel)
    except OSError:
        pytest.skip("当前环境不能创建符号链接")
    assert main(["spec", "init", "--root", str(root)]) == 2
    assert sentinel.read_text(encoding="utf-8") == "keep\n"
    assert link.is_symlink()


def test_check_fails_until_empty_markers_are_gone(root, capsys):
    assert main(["spec", "--root", str(root)]) == 0
    listed = capsys.readouterr().out
    assert "无文件" in listed and "不要求补" in listed and "legacy.Old" in listed
    assert main(["spec", "--check", "--root", str(root)]) == 1
    assert main(["spec", "init", "--root", str(root)]) == 0
    assert main(["spec", "--check", "--root", str(root)]) == 1
    for module_id in ("gameplay.Jigsaw", "gameplay.Jigsaw.Board"):
        for name in ("程序设计.md", "模块现状.md"):
            path = _folder(root, module_id) / name
            path.write_text(path.read_text(encoding="utf-8").replace("<!-- spec:empty -->\n", ""), encoding="utf-8")
    assert main(["spec", "--check", "--root", str(root)]) == 0
    assert main(["spec", "--root", str(root)]) == 0


def test_mentioning_empty_marker_in_prose_is_not_incomplete(root, capsys):
    """规格正文用反引号提到空标记字面量时，不能误判为首稿未完成（feature.Spec 自述会踩）。"""
    assert main(["spec", "init", "--root", str(root)]) == 0
    for module_id in ("gameplay.Jigsaw", "gameplay.Jigsaw.Board"):
        for name in ("程序设计.md", "模块现状.md"):
            path = _folder(root, module_id) / name
            body = path.read_text(encoding="utf-8").replace("<!-- spec:empty -->\n", "", 1)
            path.write_text(body + "\n空标记原文是 `<!-- spec:empty -->`。\n", encoding="utf-8")
    assert main(["spec", "--check", "--root", str(root)]) == 0
    assert main(["spec", "--root", str(root)]) == 0
    assert "gameplay.Jigsaw  已有规格" in capsys.readouterr().out


def test_index_lists_gaps_without_changing_completion(root):
    assert main(["spec", "init", "--root", str(root)]) == 0
    assert main(["spec", "index", "--root", str(root)]) == 0
    catalog = (root / ".memory" / "specs" / "index.md").read_text(encoding="utf-8")
    row = next(line for line in catalog.splitlines() if line.startswith("| [gameplay.Jigsaw]("))
    assert "策划、美术" in row and "首稿未完成" in row
    folder = _folder(root, "gameplay.Jigsaw")
    plan = folder / "策划设计.md"
    plan.write_text(plan.read_text(encoding="utf-8").replace("<!-- spec:design-gap -->\n", ""), encoding="utf-8")
    (folder / "美术设计.md").unlink()
    kept = plan.read_text(encoding="utf-8")
    assert main(["spec", "index", "--root", str(root)]) == 0
    assert plan.read_text(encoding="utf-8") == kept
    assert not (folder / "美术设计.md").exists()
    catalog = (root / ".memory" / "specs" / "index.md").read_text(encoding="utf-8")
    row = next(line for line in catalog.splitlines() if line.startswith("| [gameplay.Jigsaw]("))
    assert "缺美术节" in row and "策划" not in row
    assert main(["spec", "--check", "--root", str(root)]) == 1
    for module_id in ("gameplay.Jigsaw", "gameplay.Jigsaw.Board"):
        for name in ("程序设计.md", "模块现状.md"):
            path = _folder(root, module_id) / name
            path.write_text(path.read_text(encoding="utf-8").replace("<!-- spec:empty -->\n", ""), encoding="utf-8")
    assert main(["spec", "--check", "--root", str(root)]) == 0


def test_legacy_single_file_splits_without_mixing_art(root):
    specs = root / ".memory" / "specs"
    specs.mkdir()
    (specs / "gameplay.Jigsaw.md").write_text(
        "---\nmodule: gameplay.Jigsaw\nupdated: '2026-10-23'\n---\n\n"
        "<!-- spec:facts:start -->\n- 上级：无\n<!-- spec:facts:end -->\n\n"
        "## 策划设计\n\n策划正文\n\n## 美术设计\n\n只给美术\n\n"
        "## 程序设计\n\n程序正文\n\n## 模块现状\n\n现状正文\n",
        encoding="utf-8")
    assert main(["spec", "index", "--root", str(root)]) == 0
    folder = _folder(root, "gameplay.Jigsaw")
    assert not (specs / "gameplay.Jigsaw.md").exists()
    assert "只给美术" in (folder / "美术设计.md").read_text(encoding="utf-8")
    assert "程序正文" not in (folder / "美术设计.md").read_text(encoding="utf-8")
    assert "程序正文" in (folder / "程序设计.md").read_text(encoding="utf-8")
    assert "src/Jigsaw/**" in (folder / "index.md").read_text(encoding="utf-8")


def test_init_keeps_custom_spec_dir_and_writes_skill(root):
    (root / '.memory' / 'config.yaml').write_text(
        CONFIG + 'spec: { dir: .memory/custom-specs }\n', encoding='utf-8')
    assert main(['init', '--root', str(root), '--agents', 'cursor']) == 0
    assert 'custom-specs' in (root / '.memory' / 'config.yaml').read_text(encoding='utf-8')
    skill = (root / '.cursor' / 'skills' / 'pmem-spec' / 'SKILL.md').read_text(encoding='utf-8')
    assert 'pmem spec' in skill
    assert 'spec:design-gap' in skill
    assert '数值' in skill and '边界' in skill and '表现' in skill and '规则' in skill
    assert '美术设计.md' in skill and '本模块无画面' in skill
    assert '子模块' in skill and '留空' in skill and '请打开某文件' in skill
    assert '现在的设计' in skill
    assert '一句一行' in skill
    assert '不要整篇重写' in skill
    assert 'search_memory' in skill
    assert '新模块' in skill
    assert '补全模块规格' in skill
    assert 'pmem spec fill' in skill
    assert 'pmem spec complete' in skill
    assert '反推' in skill
    assert '闭集词表' in skill
    assert '所有权' in skill
    assert '合上代码' in skill
    assert '单独拿走' in skill
    assert '一样' in skill and '相似' in skill
    assert '依赖规格' in skill
    assert '反推循环' in skill
    assert '入参字段闭集' in skill
    assert '出参字段闭集' in skill
    assert '生成物' in skill
    assert '按字面抄' in skill
    assert '停手' in skill
    assert '九成' in skill
    assert '九成八' in skill
    assert '失败条件' in skill
    assert '配置与环境变量' in skill
    assert '含某某' in skill


def test_project_init_lays_spec_skeletons(root, capsys):
    assert main(["init", "--root", str(root), "--agents", "cursor"]) == 0
    out = capsys.readouterr().out
    assert "规格骨架：新写" in out
    assert "补全模块规格" in out
    assert (_folder(root, "gameplay.Jigsaw") / "策划设计.md").is_file()


def test_fill_lists_incomplete_modules_without_writing_prose(root, capsys):
    assert main(["spec", "fill", "--root", str(root)]) == 1
    out = capsys.readouterr().out
    assert "gameplay.Jigsaw" in out and "gameplay.Jigsaw.Board" in out
    assert "legacy.Old" not in out
    assert "不写正文" in out
    assert "合上代码反推" in out
    assert "单独拿走" in out
    program = _folder(root, "gameplay.Jigsaw") / "程序设计.md"
    assert "<!-- spec:empty -->" in program.read_text(encoding="utf-8")
    for module_id in ("gameplay.Jigsaw", "gameplay.Jigsaw.Board"):
        for name in ("程序设计.md", "模块现状.md"):
            path = _folder(root, module_id) / name
            path.write_text(path.read_text(encoding="utf-8").replace("<!-- spec:empty -->\n", ""), encoding="utf-8")
    assert main(["spec", "fill", "--root", str(root)]) == 0
    done = capsys.readouterr().out
    assert "都已写完" in done
    assert "合上代码反推" in done
    assert "九成八" in done
    assert "<!-- spec:empty -->" not in program.read_text(encoding="utf-8")


def test_complete_is_the_fill_entry_and_names_the_goal(root, capsys):
    assert main(["spec", "complete", "--root", str(root)]) == 1
    out = capsys.readouterr().out
    assert "补全模块规格" in out
    assert "九成" in out
    assert "九成八" in out
    assert "失败条件" in out
    assert "配置与环境变量" in out
    assert "gameplay.Jigsaw" in out
    assert "不写正文" in out
    assert "<!-- spec:empty -->" in (_folder(root, "gameplay.Jigsaw") / "程序设计.md").read_text(encoding="utf-8")


def test_fill_with_no_modules_does_not_claim_they_are_done(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("PMEM_CACHE_DIR", str(tmp_path / "cache"))
    root = tmp_path / "proj"
    (root / ".memory").mkdir(parents=True)
    (root / ".memory" / "config.yaml").write_text(CONFIG, encoding="utf-8")
    (root / ".memory" / "modules.yaml").write_text("categories: { gameplay: {} }\nmodules: {}\n", encoding="utf-8")
    assert main(["spec", "fill", "--root", str(root)]) == 0
    out = capsys.readouterr().out
    assert "还没有已登记模块" in out
    assert "都已写完" not in out
    assert not (root / ".memory" / "specs").exists()


def test_init_survives_an_unreadable_module_list(tmp_path, capsys):
    root = tmp_path / "proj"
    (root / ".memory").mkdir(parents=True)
    (root / ".memory" / "config.yaml").write_text(CONFIG, encoding="utf-8")
    (root / ".memory" / "modules.yaml").write_text("modules: [\n", encoding="utf-8")
    assert main(["init", "--root", str(root), "--agents", "cursor"]) == 0
    out = capsys.readouterr().out
    assert "规格骨架未写" in out
    assert "下一步" in out
