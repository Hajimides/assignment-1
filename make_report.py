"""将三份搭配词 CSV 汇总为可离线打开的 output/results.html。"""

import csv
import hashlib
import json
from html import escape
from pathlib import Path


COLUMNS = [
    ("collocate", "搭配词"),
    ("obs_local", "实际共现"),
    ("exp_local", "预期共现"),
    ("ratio_local", "实际 / 预期"),
    ("obs_global", "全局频数"),
    ("p_value", "p 值"),
]
LABELS = {
    "window5": "窗口 5 · 左右各 5 词",
    "window10": "窗口 10 · 左右各 10 词",
    "sentence": "句子模式 · 同一句共现",
}


def file_hash(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_table(rows):
    headers = []
    for key, label in COLUMNS:
        order = ' aria-sort="descending"' if key == "obs_local" else ""
        headers.append(
            f'<th scope="col"{order}><button type="button" data-key="{key}">'
            f'{label}<span aria-hidden="true"> ↕</span></button></th>'
        )
    body = []
    for row in rows:
        cells = []
        for key, _ in COLUMNS:
            value = row[key]
            if key in ("exp_local", "ratio_local"):
                displayed = f"{float(value):.3f}"
            elif key == "p_value":
                displayed = f"{float(value):.4g}"
            else:
                displayed = value
            cells.append(f'<td data-value="{escape(value, quote=True)}">{escape(displayed)}</td>')
        body.append(
            f'<tr data-word="{escape(row["collocate"], quote=True)}">'
            + "".join(cells) + "</tr>"
        )
    return (
        '<table><thead><tr>' + "".join(headers) + '</tr></thead><tbody>'
        + "".join(body) + '</tbody></table>'
    )


def main():
    project_dir = Path(__file__).resolve().parent
    output_dir = project_dir / "output"
    metadata = json.loads((output_dir / "analysis_settings.json").read_text(encoding="utf-8"))
    stats = json.loads((output_dir / "preprocessing_stats.json").read_text(encoding="utf-8"))
    if file_hash(project_dir / stats["source_file"]) != stats["source_sha256"]:
        raise ValueError("原始语料已变化，请依次重跑 segment.py 和 collocates.py。")
    current_hash = file_hash(project_dir / "sentences.txt")
    if current_hash != metadata["sentences_sha256"] or current_hash != stats["sentences_sha256"]:
        raise ValueError("分词文件与分析记录不一致，请依次重跑 segment.py 和 collocates.py。")

    cards = []
    sections = []
    for run in metadata["runs"]:
        csv_path = output_dir / run["csv"]
        if file_hash(csv_path) != run["csv_sha256"]:
            raise ValueError(f"{csv_path.name} 已变化，请重新运行 collocates.py。")
        with csv_path.open(encoding="utf-8-sig", newline="") as csv_file:
            rows = list(csv.DictReader(csv_file))
        if len(rows) != run["rows"]:
            raise ValueError(f"{csv_path.name} 的行数与分析记录不一致。")
        for row in rows:
            if not (0 <= float(row["p_value"]) < metadata["max_p"]):
                raise ValueError(f"{csv_path.name} 含有不符合 p 值要求的结果。")
        name = run["name"]
        label = LABELS[name]
        cards.append(f'<div class="card"><span>{label}</span><strong>{len(rows)}</strong><small>显著搭配词</small></div>')
        sections.append(
            f'<section class="result" data-mode="{name}" aria-labelledby="heading-{name}">'
            f'<div class="section-top"><div><h2 id="heading-{name}">{label}</h2>'
            f'<p class="row-count">显示 {len(rows)} / {len(rows)} 项</p></div>'
            f'<a class="download" href="{escape(run["csv"], quote=True)}" download>下载 CSV ↓</a></div>'
            '<div class="table-scroll">' + build_table(rows) + '</div>'
            '<p class="empty" hidden>没有匹配的搭配词，请修改搜索内容。</p></section>'
        )

    template = r'''<!doctype html>
<html lang="zh-Hans">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>祥子 · 搭配词比较</title>
  <style>
    :root { color-scheme: light; --ink:#19332f; --muted:#596d65; --line:#d9e2d8; --accent:#17664f; }
    * { box-sizing:border-box; }
    body { margin:0; background:#f5f6ef; color:var(--ink); font-family:system-ui,-apple-system,"PingFang SC","Microsoft YaHei",sans-serif; line-height:1.65; }
    main { max-width:1160px; margin:auto; padding:40px 24px 60px; }
    .eyebrow { color:var(--accent); font-size:13px; font-weight:700; letter-spacing:.12em; margin:0; }
    h1 { margin:8px 0 12px; font-size:clamp(28px,5vw,44px); line-height:1.25; }
    .intro,.meta { color:var(--muted); margin:0 0 12px; }
    .cards { display:grid; grid-template-columns:repeat(3,1fr); gap:16px; margin:24px 0; }
    .card { background:#fff; border:1px solid var(--line); border-radius:14px; padding:18px 22px; }
    .card span,.card small { display:block; color:var(--muted); }
    .card strong { display:block; color:var(--accent); font-size:36px; line-height:1.5; }
    details { background:#edf1e7; border-radius:12px; padding:14px 18px; margin-bottom:24px; }
    summary { cursor:pointer; font-weight:650; }
    details p { margin:10px 0; }
    .controls { display:flex; flex-wrap:wrap; align-items:end; gap:14px; margin:24px 0; }
    label { display:flex; flex-direction:column; gap:5px; font-size:14px; font-weight:600; }
    select,input { min-height:44px; border:1px solid #9eafa2; border-radius:8px; padding:8px 12px; font:inherit; color:var(--ink); background:white; }
    input { width:260px; max-width:100%; }
    button { font:inherit; cursor:pointer; }
    #reset { min-height:44px; padding:8px 16px; border:1px solid #9eafa2; border-radius:8px; background:white; color:var(--ink); }
    button:focus-visible,input:focus-visible,select:focus-visible,a:focus-visible,summary:focus-visible { outline:3px solid #c17322; outline-offset:3px; }
    #status { color:var(--muted); font-size:14px; }
    .result { background:white; border:1px solid var(--line); border-radius:14px; margin:18px 0; overflow:hidden; }
    .section-top { display:flex; align-items:center; justify-content:space-between; gap:12px; padding:20px 22px; }
    h2 { font-size:20px; margin:0; }
    .row-count { color:var(--muted); font-size:14px; margin:4px 0 0; }
    a { color:var(--accent); text-underline-offset:3px; }
    .download { white-space:nowrap; font-size:14px; }
    .table-scroll { overflow-x:auto; }
    table { border-collapse:collapse; width:100%; min-width:660px; font-size:14px; font-variant-numeric:tabular-nums; }
    th { background:#eaf0e7; text-align:right; border-top:1px solid var(--line); border-bottom:1px solid var(--line); }
    th button { display:block; width:100%; padding:12px 16px; text-align:inherit; border:0; background:transparent; color:var(--ink); font-weight:650; }
    th[aria-sort] { background:#d9e9dd; }
    td { padding:10px 16px; text-align:right; border-bottom:1px solid #edf0ea; }
    th:first-child,td:first-child { text-align:left; }
    td:first-child { font-weight:600; }
    tbody tr:hover { background:#f6f8f1; }
    .empty { color:var(--muted); padding:0 22px 18px; }
    footer { color:var(--muted); font-size:13px; margin-top:28px; }
    [hidden] { display:none !important; }
    @media(max-width:620px) { main { padding:26px 14px 40px; } .cards { grid-template-columns:1fr; gap:8px; } .card { display:flex; align-items:center; justify-content:space-between; gap:12px; padding:12px 16px; } .card strong { font-size:28px; } .card small { display:none; } .controls label { width:100%; } input { width:100%; } .section-top { padding:16px; } h2 { font-size:17px; } }
  </style>
</head>
<body>
<main>
  <header>
    <p class="eyebrow">CHI3242 · ASSIGNMENT 1</p>
    <h1>祥子的语言环境</h1>
    <p class="intro">《骆驼祥子》搭配词比较：观察窗口大小与共现单位怎样影响结果。</p>
    <p class="meta">语料：老舍《骆驼祥子》 · 目标词：祥子 · __SENTENCES__ 个句子 · __TOKENS__ 个词 · 目标词出现 __TARGET_COUNT__ 次</p>
  </header>
  <div class="cards">__CARDS__</div>
  <details open>
    <summary>怎样读这三组结果</summary>
    <p>三组均使用 Fisher 精确检验，方向为 greater，保留至少 2 字的词和原始 p &lt; 0.05 的结果，并过滤 __STOPWORDS__ 个停用词。初始排序为实际共现次数从高到低。</p>
    <p>“预期共现”是在独立假设下的预期计数；“实际 / 预期”大于 1 表示观察到的共现高于预期。p 值是检验结果，不能直接当作文学解释正确的概率。</p>
    <p>窗口模式统计目标词语境内的词语位置；句子模式统计包含目标词和搭配词的句子数，同一句重复出现也只计一次。两种模式的共现计数单位不同，比较时请关注词语、排序和关联比例。</p>
    <p>点击表头可排序；下方可以切换表格、搜索词语或只看前 20 项。原始 CSV 始终保留全部结果。</p>
  </details>
  <div class="controls">
    <label for="mode">比较范围<select id="mode"><option value="all">全部三组</option><option value="window5">窗口 5</option><option value="window10">窗口 10</option><option value="sentence">句子模式</option></select></label>
    <label for="search">搜索搭配词<input id="search" type="search" placeholder="例如：心中、虎妞、小福子" autocomplete="off"></label>
    <label for="limit">显示数量<select id="limit"><option value="all">全部结果</option><option value="20">前 20 项</option></select></label>
    <button id="reset" type="button">重置</button>
  </div>
  <p id="status" role="status" aria-live="polite"></p>
  __SECTIONS__
  <footer>
    <p>原始语料来自 <a href="https://github.com/mcjkurz/qhchina-data/blob/main/corpora/中文小说100强/3_骆驼祥子.txt">mcjkurz/qhchina-data</a>。预处理去掉目录、书名、版次、独立章节编号和结束标记，转简体后分句、分词，只保留至少 5 个词的句子。</p>
    <p>本页呈现统计结果，文学解释由报告完成。参数与处理规模：<a href="analysis_settings.json">分析设置</a> · <a href="preprocessing_stats.json">预处理统计</a>。qhchina __VERSION__；本次使用原始 p 值，未做多重检验校正。</p>
  </footer>
</main>
<script>
  const mode = document.getElementById('mode');
  const search = document.getElementById('search');
  const limit = document.getElementById('limit');
  const sections = Array.from(document.querySelectorAll('.result'));
  const initialRows = new Map(sections.map(section => [section, Array.from(section.querySelectorAll('tbody tr'))]));
  function update() {
    const query = search.value.trim();
    let total = 0;
    let visibleSections = 0;
    sections.forEach(section => {
      section.hidden = mode.value !== 'all' && mode.value !== section.dataset.mode;
      const rows = Array.from(section.querySelectorAll('tbody tr'));
      let matches = 0;
      let shown = 0;
      rows.forEach(row => {
        const match = row.dataset.word.includes(query);
        if (match) matches++;
        const show = match && (limit.value === 'all' || shown < Number(limit.value));
        row.hidden = !show;
        if (show) shown++;
      });
      section.querySelector('.row-count').textContent = `显示 ${shown} / ${rows.length} 项 · 匹配 ${matches} 项`;
      section.querySelector('.empty').hidden = matches !== 0;
      if (!section.hidden) { total += shown; visibleSections++; }
    });
    document.getElementById('status').textContent = `当前显示 ${visibleSections} 组，共 ${total} 项。`;
  }
  sections.forEach(section => {
    section.querySelectorAll('th button').forEach((button, index) => {
      button.addEventListener('click', () => {
        const th = button.closest('th');
        const ascending = th.getAttribute('aria-sort') === 'descending';
        const rows = Array.from(section.querySelectorAll('tbody tr'));
        rows.sort((a,b) => {
          const av = a.cells[index].dataset.value;
          const bv = b.cells[index].dataset.value;
          const result = button.dataset.key === 'collocate' ? av.localeCompare(bv,'zh-Hans') : Number(av) - Number(bv);
          return ascending ? result : -result;
        });
        section.querySelectorAll('th').forEach(header => header.removeAttribute('aria-sort'));
        th.setAttribute('aria-sort', ascending ? 'ascending' : 'descending');
        rows.forEach(row => section.querySelector('tbody').appendChild(row));
        update();
      });
    });
  });
  mode.addEventListener('change',update);
  search.addEventListener('input',update);
  limit.addEventListener('change',update);
  document.getElementById('reset').addEventListener('click',() => {
    mode.value = 'all'; search.value = ''; limit.value = 'all';
    sections.forEach(section => {
      initialRows.get(section).forEach(row => section.querySelector('tbody').appendChild(row));
      section.querySelectorAll('th').forEach(th => th.removeAttribute('aria-sort'));
      section.querySelector('button[data-key="obs_local"]').closest('th').setAttribute('aria-sort','descending');
    });
    update();
  });
  update();
</script>
</body>
</html>
'''
    replacements = {
        "__SENTENCES__": f'{metadata["sentence_count"]:,}',
        "__TOKENS__": f'{metadata["token_count"]:,}',
        "__TARGET_COUNT__": str(metadata["target_token_count"]),
        "__STOPWORDS__": str(metadata["stopword_count"]),
        "__VERSION__": escape(metadata["qhchina_version"]),
        "__CARDS__": "".join(cards),
        "__SECTIONS__": "\n".join(sections),
    }
    for placeholder, value in replacements.items():
        template = template.replace(placeholder, value)
    output_path = output_dir / "results.html"
    output_path.write_text(template, encoding="utf-8")
    print(f"已生成：{output_path}")


if __name__ == "__main__":
    main()
