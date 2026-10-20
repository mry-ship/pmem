"""记忆图的两种输出：本地 HTML（可缩放、点开看全文，数据内嵌、不联网）和 Wiki 里的 Mermaid 图。"""
from __future__ import annotations

import html
import json
from pathlib import Path

MAP_FILE = "map.html"
MERMAID_MAX_NODES = 40
MERMAID_TITLE_CHARS = 24
# Wiki 目录首次生成时放的 .gitignore：派生视图默认不进版本库；删掉它就会被提交，之后也不会再生成
SELF_IGNORE = "*\n"
_CLASSES = (
    "classDef fail fill:#fde2e1,stroke:#c9302c,color:#222",
    "classDef landed fill:#dff0d8,stroke:#3c763d,color:#222",
    "classDef caution fill:#fcf3d0,stroke:#b8860b,color:#222",
    "classDef pending fill:#e3e7f8,stroke:#4a5bbf,color:#222",
    "classDef old fill:#f4f4f4,stroke:#999,color:#777,stroke-dasharray:3 3",
)


def _mermaid_text(text: str) -> str:
    """Mermaid 带引号标签里的字符转义：先换 #，再换引号和尖括号。"""
    return (text.replace("#", "#35;").replace('"', "#34;").replace("<", "#60;").replace(">", "#62;")
            .replace("\n", " "))


def render_mermaid(module: dict, limit: int = MERMAID_MAX_NODES) -> str | None:
    """一个模块的演化图（build_map 的模块项）：每个议题一个分组，从新到旧放议题，节点总数超过 limit 时后面的不画。
    只有一条记忆、也没有任何关系的模块不画。"""
    topics, count = [], 0
    for topic in module["topics"]:
        if topics and count + len(topic["nodes"]) > limit:
            break
        topics.append(topic)
        count += len(topic["nodes"])
    drawn = {n["id"] for t in topics for n in t["nodes"]}
    edges = [e for t in topics for e in t["edges"] if e["from"] in drawn and e["to"] in drawn]
    if count < 2 and not edges:
        return None
    lines = ["```mermaid", "flowchart LR"]
    for i, topic in enumerate(topics):
        lines.append(f'  subgraph t{i}["{_mermaid_text(topic["entity"])}"]')
        lines.append("    direction LR")
        for n in topic["nodes"]:
            title = n["title"] if len(n["title"]) <= MERMAID_TITLE_CHARS else n["title"][:MERMAID_TITLE_CHARS] + "…"
            css = n["group"] if n["current"] else "old"
            lines.append(f'    n{n["id"]}["{_mermaid_text(n["label"])} {n["date"][5:]}<br/>{_mermaid_text(title)}"]:::{css}')
        lines.append("  end")
    for e in edges:
        arrow = {"supersedes": "-->|替代|", "inferred": "-.->|推断|", "reverted": "-.->|已撤销|"}[e["type"]]
        lines.append(f"  n{e['from']} {arrow} n{e['to']}")
    lines += [f"  {c}" for c in _CLASSES]
    lines.append("```")
    hidden = len(module["topics"]) - len(topics)
    if hidden:
        lines.append(f"\n另有 {hidden} 个较早的议题没画出，完整的图用 `pmem map` 生成。")
    return "\n".join(lines)


def render_map_html(model: dict) -> str:
    data = json.dumps(model, ensure_ascii=False).replace("</", "<\\/")
    return _HTML.replace("__TITLE__", html.escape(str(model.get("title") or ""))).replace("__DATA__", data)


def write_map_html(model: dict, out: Path) -> Path:
    """out 是 HTML 文件路径；所在目录不存在时新建，并放 .gitignore（派生视图不进版本库）。"""
    if not out.parent.exists():
        out.parent.mkdir(parents=True)
        (out.parent / ".gitignore").write_text(SELF_IGNORE, encoding="utf-8", newline="\n")
    out.write_text(render_map_html(model), encoding="utf-8", newline="\n")
    return out


_HTML = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<title>__TITLE__ 记忆图</title>
<style>
  html, body { height: 100%; }
  body { margin: 0; font: 14px/1.5 -apple-system, "Segoe UI", "Microsoft YaHei", sans-serif; color: #222;
         display: flex; flex-direction: column; }
  header { padding: 10px 16px; border-bottom: 1px solid #ddd; background: #fafafa; }
  header h1 { font-size: 18px; margin: 0 0 4px; }
  .stats span { display: inline-block; margin-right: 14px; }
  .stats b { font-size: 16px; }
  .bad { color: #c9302c; }
  .note { color: #777; font-size: 12px; }
  #checks { display: flex; gap: 8px; flex-wrap: wrap; margin-top: 6px; }
  #checks details { border: 1px solid #ddd; border-radius: 4px; padding: 2px 8px; background: #fff; max-width: 520px; }
  #checks li { cursor: pointer; font-size: 12px; }
  #checks li:hover { text-decoration: underline; }
  .bar { margin-top: 6px; display: flex; gap: 12px; align-items: center; flex-wrap: wrap; }
  .legend i { display: inline-block; width: 10px; height: 10px; border-radius: 50%; margin: 0 4px 0 10px; }
  #checks ul { max-height: 30vh; overflow: auto; margin: 4px 0; padding-left: 18px; }
  main { display: flex; flex: 1; min-height: 0; }
  #view { flex: 1; min-width: 0; overflow: hidden; cursor: grab; background: #fff; }
  #view:active { cursor: grabbing; }
  aside { width: clamp(220px, 30vw, 420px); border-left: 1px solid #ddd; padding: 12px 16px; overflow: auto;
          background: #fcfcfc; }
  aside pre { white-space: pre-wrap; font: inherit; background: #fff; border: 1px solid #eee; padding: 8px; }
  aside a { color: #2a6db0; cursor: pointer; }
  text { font-size: 12px; fill: #333; }
  .module text { font-weight: bold; font-size: 13px; }
  .node { cursor: pointer; }
  .focus circle { stroke: #000; stroke-width: 3; }
</style>
</head>
<body>
<header>
  <h1>__TITLE__ 记忆图</h1>
  <div class="stats" id="stats"></div>
  <div id="checks"></div>
  <div class="bar">
    <input id="filter" placeholder="按模块或议题过滤" size="24">
    <label><input type="checkbox" id="onlyCurrent"> 只看现行</label>
    <span class="legend"><i style="background:#d9534f"></i>失败或纠错<i style="background:#3c9a3c"></i>落地<i
      style="background:#d4a017"></i>注意<i style="background:#5c6bc0"></i>未实现<i
      style="background:#fff;border:1px solid #999"></i>已被替代/归档</span>
    <span class="note">实线：替代 · 虚线：推断（排除项之后的落地）· 灰点线：已撤销 · 橙圈：需核实 · 滚轮缩放、拖动平移</span>
  </div>
</header>
<main>
  <div id="view"><svg id="svg" width="100%" height="100%"><g id="root"></g></svg></div>
  <aside id="detail"><p class="note">点一个节点看全文。</p></aside>
</main>
<script type="application/json" id="data">__DATA__</script>
<script>
(function () {
  const model = JSON.parse(document.getElementById("data").textContent);
  const COLORS = { fail: "#d9534f", landed: "#3c9a3c", caution: "#d4a017", pending: "#5c6bc0" };
  const NS = "http://www.w3.org/2000/svg";
  const GUTTER = 280, SLOT = 26, ROW = 34, HEAD = 30, PAD = 40;
  const root = document.getElementById("root"), svg = document.getElementById("svg");
  const byId = {};
  let view = { x: 0, y: 0, k: 1 };

  function el(tag, attrs, parent) {
    const node = document.createElementNS(NS, tag);
    for (const k in attrs) node.setAttribute(k, attrs[k]);
    if (parent) parent.appendChild(node);
    return node;
  }
  function text(parent, x, y, value, cls) {
    const t = el("text", { x: x, y: y }, parent);
    if (cls) t.setAttribute("class", cls);
    t.textContent = value;
    return t;
  }

  function stats() {
    const s = model.summary, c = s.coverage, box = document.getElementById("stats");
    const rate = c.active ? Math.round(100 * c.recorded / c.active) + "%（" + c.recorded + "/" + c.active + "）" : "近期没有提交";
    const items = [["模块", s.modules], ["现行记忆", s.current + " / 共 " + s.total], ["功能记录覆盖（近 " + model.days + " 天）", rate],
      ["漏记", s.gaps, s.gaps], ["断链", s.broken, s.broken], ["悬而未决", s.unresolved, s.unresolved], ["过期", s.stale, s.stale]];
    for (const [label, value, bad] of items) {
      const span = document.createElement("span");
      span.textContent = label + " ";
      const b = document.createElement("b");
      b.textContent = value;
      if (bad) b.className = "bad";
      span.appendChild(b);
      box.appendChild(span);
    }
    const note = document.createElement("div");
    note.className = "note";
    note.textContent = "生成于 " + model.generated + "。这些衡量存储结构是否完整，不衡量对 AI 是否有用（看 pmem report 与 pmem bench）。";
    box.appendChild(note);
    const names = { gaps: "漏记", broken: "断链", unresolved: "悬而未决", stale: "过期" };
    const checks = document.getElementById("checks");
    for (const key of ["gaps", "broken", "unresolved", "stale"]) {
      const rows = model.checks[key];
      if (!rows.length) continue;
      const d = document.createElement("details"), sum = document.createElement("summary"), ul = document.createElement("ul");
      sum.textContent = names[key] + " " + rows.length;
      d.appendChild(sum);
      for (const r of rows) {
        const li = document.createElement("li");
        li.textContent = key === "gaps" ? r.module + "：" + r.commits + " 次提交，同期没有功能记录"
          : r.module + " / " + r.entity + (r.reason ? "：" + r.reason : "");
        if (r.ids) li.onclick = () => focus(r.ids[0]);
        else li.onclick = () => { document.getElementById("filter").value = r.module; draw(); };
        ul.appendChild(li);
      }
      d.appendChild(ul);
      checks.appendChild(d);
    }
  }

  function draw() {
    while (root.firstChild) root.removeChild(root.firstChild);
    const word = document.getElementById("filter").value.trim().toLowerCase();
    const only = document.getElementById("onlyCurrent").checked;
    const rows = [];
    for (const m of model.modules) {
      const topics = [];
      for (const t of m.topics) {
        if (word && !(m.module + " " + t.entity).toLowerCase().includes(word)) continue;
        const nodes = t.nodes.filter(n => !only || n.current);
        if (nodes.length) topics.push({ topic: t, nodes: nodes });
      }
      if (topics.length) rows.push({ module: m, topics: topics });
    }
    const dates = [...new Set(rows.flatMap(r => r.topics.flatMap(t => t.nodes.map(n => n.date))))].sort();
    const width = {};
    for (const d of dates) width[d] = 1;
    for (const r of rows) for (const t of r.topics) {
      const per = {};
      for (const n of t.nodes) per[n.date] = (per[n.date] || 0) + 1;
      for (const d in per) width[d] = Math.max(width[d], per[d]);
    }
    const colX = {};
    let x = GUTTER;
    for (const d of dates) { colX[d] = x; x += width[d] * SLOT + PAD; }
    const axis = el("g", {}, root);
    for (const d of dates) text(axis, colX[d], 16, d.slice(5));
    let y = 40;
    const pos = {};
    const nodesLayer = el("g", {}), edgesLayer = el("g", {});
    for (const r of rows) {
      const g = el("g", { class: "module" }, root);
      el("rect", { x: 0, y: y, width: x, height: HEAD - 4, fill: "#eef2f7" }, g);
      text(g, 8, y + 18, r.module.module + "（现行 " + r.module.current + " / 共 " + r.module.total + "）");
      y += HEAD;
      for (const t of r.topics) {
        text(root, 20, y + 20, t.topic.entity.length > 30 ? t.topic.entity.slice(0, 30) + "…" : t.topic.entity);
        el("line", { x1: GUTTER - 10, y1: y + 16, x2: x, y2: y + 16, stroke: "#f0f0f0" }, root);
        const used = {};
        for (const n of t.nodes) {
          const k = used[n.date] = (used[n.date] || 0) + 1;
          const cx = colX[n.date] + (k - 1) * SLOT + 10, cy = y + 16;
          pos[n.id] = [cx, cy];
          byId[n.id] = { node: n, module: r.module.module, entity: t.topic.entity };
          const ng = el("g", { class: "node", "data-id": n.id }, nodesLayer);
          if (n.stale) el("circle", { cx: cx, cy: cy, r: 12, fill: "none", stroke: "#f0ad4e", "stroke-width": 3 }, ng);
          el("circle", { cx: cx, cy: cy, r: 8, fill: n.current ? COLORS[n.group] : "#fff",
                         stroke: COLORS[n.group], "stroke-width": 2 }, ng);
          const tip = el("title", {}, ng);
          tip.textContent = n.label + " " + n.date + "：" + n.title;
          ng.onclick = () => show(n.id);
        }
        y += ROW;
      }
      y += 8;
    }
    for (const r of rows) for (const t of r.topics) for (const e of t.topic.edges) {
      const a = pos[e.from], b = pos[e.to];
      if (!a || !b) continue;
      const style = e.type === "inferred" ? { stroke: "#888", "stroke-dasharray": "5 4" }
        : e.type === "reverted" ? { stroke: "#bbb", "stroke-dasharray": "2 3" } : { stroke: "#555" };
      const mid = (a[0] + b[0]) / 2, bend = a[1] === b[1] ? -14 : 0;
      el("path", Object.assign({ d: "M" + a[0] + "," + a[1] + " Q" + mid + "," + (Math.min(a[1], b[1]) + bend) + " " + b[0] + "," + b[1],
                                 fill: "none", "stroke-width": 1.5 }, style), edgesLayer);
    }
    root.appendChild(edgesLayer);
    root.appendChild(nodesLayer);
    apply();
  }

  function show(id) {
    const hit = byId[id], box = document.getElementById("detail");
    while (box.firstChild) box.removeChild(box.firstChild);
    if (!hit) return;
    const n = hit.node;
    const add = (tag, value) => { const e = document.createElement(tag); e.textContent = value; box.appendChild(e); return e; };
    add("h3", n.label + " · " + hit.module + " / " + hit.entity);
    add("div", n.date + " · " + n.author + " · " + (n.current ? "现行" : n.status === "archived" ? "已归档" : "已被替代")
      + (n.reverted ? " · 合并已于 " + n.reverted + " 撤销" : "") + (n.project ? " · 全项目" : "")).className = "note";
    add("p", n.title).style.fontWeight = "bold";
    if (n.stale) add("p", "⚠ 需核实：" + n.stale.join("；")).className = "bad";
    if (n.applies) add("p", "适用条件：" + n.applies);
    add("pre", n.content || "");
    if (n.anchors) add("p", "关联代码：" + n.anchors.join("，"));
    if (n.superseded_by) {
      const p = add("p", "被替代：");
      const a = document.createElement("a");
      a.textContent = n.superseded_by;
      a.onclick = () => focus(n.superseded_by);
      p.appendChild(a);
    }
    add("p", "id " + n.id).className = "note";
  }

  function focus(id) {
    if (!byId[id]) { document.getElementById("filter").value = ""; document.getElementById("onlyCurrent").checked = false; draw(); }
    const g = root.querySelector('[data-id="' + id + '"]');
    root.querySelectorAll(".focus").forEach(e => e.classList.remove("focus"));
    if (!g) return;
    g.classList.add("focus");
    const c = g.querySelector("circle:last-of-type"), rect = svg.getBoundingClientRect();
    view.x = rect.width / 2 - c.cx.baseVal.value * view.k;
    view.y = rect.height / 2 - c.cy.baseVal.value * view.k;
    apply();
    show(id);
  }

  function apply() { root.setAttribute("transform", "translate(" + view.x + "," + view.y + ") scale(" + view.k + ")"); }
  svg.addEventListener("wheel", ev => {
    ev.preventDefault();
    const rect = svg.getBoundingClientRect(), mx = ev.clientX - rect.left, my = ev.clientY - rect.top;
    const k = Math.min(4, Math.max(0.1, view.k * (ev.deltaY < 0 ? 1.15 : 1 / 1.15)));
    view.x = mx - (mx - view.x) * k / view.k;
    view.y = my - (my - view.y) * k / view.k;
    view.k = k;
    apply();
  }, { passive: false });
  let drag = null;
  svg.addEventListener("mousedown", ev => { drag = [ev.clientX - view.x, ev.clientY - view.y]; });
  window.addEventListener("mousemove", ev => { if (drag) { view.x = ev.clientX - drag[0]; view.y = ev.clientY - drag[1]; apply(); } });
  window.addEventListener("mouseup", () => { drag = null; });
  document.getElementById("filter").addEventListener("input", draw);
  document.getElementById("onlyCurrent").addEventListener("change", draw);
  stats();
  draw();
})();
</script>
</body>
</html>
"""
