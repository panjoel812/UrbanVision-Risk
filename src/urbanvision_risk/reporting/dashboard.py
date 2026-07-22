# ruff: noqa: E501
from __future__ import annotations

import json
from typing import Any

_TEMPLATE = """<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>UrbanVision-Risk · Local Report</title>
  <style>
    :root {
      color-scheme: light;
      --bg: #f4f5f1;
      --surface: #ffffff;
      --surface-soft: #ebece6;
      --text: #17201c;
      --muted: #66706a;
      --border: #d7dbd5;
      --primary: #174f3e;
      --primary-soft: #dcebe4;
      --low: #4d7d68;
      --moderate: #c18a31;
      --high: #c25d36;
      --critical: #963c45;
      --na: #8b918d;
      --shadow: 0 18px 50px rgba(28, 47, 39, 0.08);
    }
    @media (prefers-color-scheme: dark) {
      :root {
        color-scheme: dark;
        --bg: #111714;
        --surface: #19211d;
        --surface-soft: #242d28;
        --text: #eff5f1;
        --muted: #aeb9b2;
        --border: #344139;
        --primary: #8ec7ad;
        --primary-soft: #263f34;
        --low: #82b89f;
        --moderate: #e1b764;
        --high: #e58a62;
        --critical: #df7f89;
        --na: #9da7a1;
        --shadow: 0 18px 50px rgba(0, 0, 0, 0.24);
      }
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      background: var(--bg);
      color: var(--text);
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      line-height: 1.5;
    }
    button, input, select { font: inherit; }
    button, select, input { color: var(--text); }
    button:focus-visible, input:focus-visible, select:focus-visible {
      outline: 3px solid color-mix(in srgb, var(--primary) 42%, transparent);
      outline-offset: 2px;
    }
    .shell { width: min(1440px, calc(100% - 32px)); margin-inline: auto; }
    .site-header { padding: 34px 0 18px; }
    .header-row { display: flex; gap: 24px; align-items: flex-start; justify-content: space-between; }
    .eyebrow {
      margin: 0 0 7px;
      color: var(--primary);
      font-size: 0.78rem;
      font-weight: 700;
      letter-spacing: 0.12em;
      text-transform: uppercase;
    }
    h1 { margin: 0; font-size: clamp(1.75rem, 4vw, 3.2rem); letter-spacing: -0.045em; line-height: 1.02; }
    .subtitle { max-width: 760px; margin: 12px 0 0; color: var(--muted); }
    .lang-button {
      border: 1px solid var(--border);
      border-radius: 999px;
      background: var(--surface);
      padding: 9px 14px;
      cursor: pointer;
      box-shadow: var(--shadow);
      white-space: nowrap;
    }
    .safety-band {
      display: flex;
      gap: 12px;
      align-items: flex-start;
      margin: 22px 0 0;
      padding: 14px 16px;
      border-left: 4px solid var(--moderate);
      background: color-mix(in srgb, var(--moderate) 10%, var(--surface));
      border-radius: 0 12px 12px 0;
    }
    .safety-mark { font-weight: 800; color: var(--moderate); }
    .safety-text { margin: 0; }
    main { padding: 18px 0 52px; }
    .stats { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 12px; }
    .stat {
      min-width: 0;
      padding: 18px;
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: 16px;
      box-shadow: var(--shadow);
    }
    .stat-label { margin: 0; color: var(--muted); font-size: 0.82rem; }
    .stat-value { margin: 5px 0 0; font-size: clamp(1.5rem, 3vw, 2.3rem); font-weight: 750; letter-spacing: -0.04em; }
    .distributions { display: grid; grid-template-columns: 1fr 1fr; gap: 18px; margin-top: 22px; }
    .section {
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: 18px;
      box-shadow: var(--shadow);
    }
    .distribution { padding: 20px; }
    .section-title { margin: 0 0 15px; font-size: 1rem; }
    .bar-row { display: grid; grid-template-columns: minmax(92px, auto) 1fr 46px; gap: 10px; align-items: center; margin: 10px 0; }
    .bar-label { font-size: 0.84rem; }
    .bar-track { height: 10px; overflow: hidden; border-radius: 999px; background: var(--surface-soft); }
    .bar-fill { height: 100%; min-width: 0; border-radius: inherit; }
    .bar-value { text-align: right; font-variant-numeric: tabular-nums; color: var(--muted); font-size: 0.84rem; }
    .tone-low { background: var(--low); }
    .tone-moderate { background: var(--moderate); }
    .tone-high { background: var(--high); }
    .tone-critical { background: var(--critical); }
    .tone-not_applicable { background: var(--na); }
    .explorer { margin-top: 22px; overflow: hidden; }
    .controls {
      display: grid;
      grid-template-columns: minmax(190px, 1.5fr) repeat(3, minmax(130px, 0.7fr));
      gap: 12px;
      padding: 16px;
      border-bottom: 1px solid var(--border);
      background: color-mix(in srgb, var(--surface-soft) 55%, var(--surface));
    }
    .field { display: grid; gap: 5px; min-width: 0; }
    .field label { color: var(--muted); font-size: 0.75rem; }
    .field input, .field select {
      width: 100%;
      border: 1px solid var(--border);
      border-radius: 10px;
      background: var(--surface);
      padding: 9px 10px;
    }
    .explorer-body { display: grid; grid-template-columns: minmax(320px, 0.8fr) minmax(0, 1.5fr); min-height: 620px; }
    .detail { padding: 18px; border-right: 1px solid var(--border); background: var(--surface); }
    .image-frame {
      aspect-ratio: 1 / 1;
      display: grid;
      place-items: center;
      overflow: hidden;
      border-radius: 14px;
      background: var(--surface-soft);
    }
    .image-frame img { width: 100%; height: 100%; object-fit: contain; }
    .image-fallback { display: none; color: var(--muted); padding: 24px; text-align: center; }
    .detail-head { display: flex; align-items: flex-start; justify-content: space-between; gap: 12px; margin-top: 16px; }
    .detail-name { margin: 0; overflow-wrap: anywhere; font-size: 1rem; }
    .score-pill {
      min-width: 64px;
      padding: 7px 10px;
      border-radius: 999px;
      text-align: center;
      font-weight: 750;
      font-variant-numeric: tabular-nums;
      color: #fff;
      background: var(--primary);
    }
    .detail-meta { display: flex; flex-wrap: wrap; gap: 8px 14px; margin: 10px 0 0; color: var(--muted); font-size: 0.8rem; }
    .recommendation { margin: 14px 0 0; padding: 11px 12px; border-radius: 10px; background: var(--primary-soft); }
    .flags { display: grid; gap: 7px; margin-top: 10px; }
    .flag { margin: 0; color: var(--high); font-size: 0.82rem; }
    .class-list { display: grid; gap: 11px; margin-top: 17px; }
    .class-row { display: grid; gap: 5px; }
    .class-line { display: flex; justify-content: space-between; gap: 12px; font-size: 0.8rem; }
    .class-line span:last-child { color: var(--muted); font-variant-numeric: tabular-nums; }
    .class-track { height: 7px; overflow: hidden; border-radius: 999px; background: var(--surface-soft); }
    .class-fill { height: 100%; border-radius: inherit; background: var(--primary); }
    .table-area { min-width: 0; background: var(--surface); }
    .table-summary { display: flex; justify-content: space-between; gap: 12px; padding: 13px 16px; color: var(--muted); font-size: 0.8rem; }
    .table-wrap { overflow-x: auto; }
    table { width: 100%; border-collapse: collapse; font-size: 0.82rem; }
    th, td { padding: 10px 12px; text-align: left; border-top: 1px solid var(--border); }
    th { color: var(--muted); font-size: 0.72rem; font-weight: 650; background: var(--surface); }
    td.num, th.num { text-align: right; font-variant-numeric: tabular-nums; }
    tbody tr { transition: background 140ms ease; }
    tbody tr:hover, tbody tr.selected { background: var(--primary-soft); }
    .select-row {
      display: inline;
      max-width: 270px;
      padding: 0;
      border: 0;
      background: transparent;
      color: var(--text);
      cursor: pointer;
      text-align: left;
      overflow-wrap: anywhere;
    }
    .badge { display: inline-block; padding: 3px 7px; border-radius: 999px; font-size: 0.72rem; border: 1px solid currentColor; }
    .badge-low { color: var(--low); }
    .badge-moderate { color: var(--moderate); }
    .badge-high { color: var(--high); }
    .badge-critical { color: var(--critical); }
    .badge-not_applicable { color: var(--na); }
    .empty { display: none; padding: 36px 18px; text-align: center; color: var(--muted); }
    footer { padding: 0 0 38px; color: var(--muted); font-size: 0.75rem; }
    .footer-line { display: flex; flex-wrap: wrap; gap: 8px 18px; }
    .hidden-lang { display: none !important; }
    @media (max-width: 980px) {
      .stats { grid-template-columns: repeat(2, minmax(0, 1fr)); }
      .controls { grid-template-columns: 1fr 1fr; }
      .explorer-body { grid-template-columns: 1fr; }
      .detail { border-right: 0; border-bottom: 1px solid var(--border); }
      .image-frame { max-width: 620px; margin-inline: auto; }
    }
    @media (max-width: 640px) {
      .shell { width: min(100% - 20px, 1440px); }
      .site-header { padding-top: 22px; }
      .header-row { display: grid; }
      .lang-button { justify-self: start; }
      .stats, .distributions, .controls { grid-template-columns: 1fr; }
      .stat { padding: 15px; }
      .distribution { padding: 16px; }
      .explorer-body { min-height: 0; }
      .detail { padding: 14px; }
      th, td { padding: 9px 10px; }
    }
    @media print {
      body { background: #fff; color: #111; }
      .lang-button, .controls, .table-area { display: none; }
      .section, .stat { box-shadow: none; }
      .explorer-body { display: block; min-height: 0; }
      .detail { border: 0; }
    }
  </style>
</head>
<body>
  <header class="site-header shell">
    <div class="header-row">
      <div>
        <p class="eyebrow">UrbanVision-Risk · v0.3</p>
        <h1><span data-zh>本地道路维护优先级报告</span><span data-en class="hidden-lang">Local road maintenance-priority report</span></h1>
        <p class="subtitle">
          <span data-zh>从已验证的 v0.2 风险结果生成；所有筛选和图片浏览都在本机完成。</span>
          <span data-en class="hidden-lang">Generated from validated v0.2 risk results; all filtering and image review stays on this device.</span>
        </p>
      </div>
      <button id="language-button" class="lang-button" type="button" aria-label="Switch language">English</button>
    </div>
    <div class="safety-band" role="note">
      <span class="safety-mark" aria-hidden="true">!</span>
      <p class="safety-text">
        <strong data-zh>维护复核优先级，不是道路安全判定。</strong>
        <strong data-en class="hidden-lang">Maintenance-review priority, not a road-safety verdict.</strong>
        <span data-zh> 本报告不能替代经过认证的工程安全鉴定；检查、封闭和维修由人工决定。</span>
        <span data-en class="hidden-lang"> This report cannot replace a certified engineering safety assessment; humans decide inspection, closure, and repair.</span>
      </p>
    </div>
  </header>

  <main class="shell">
    <section class="stats" aria-label="Batch summary">
      <article class="stat"><p class="stat-label" data-zh>图片数量</p><p class="stat-label hidden-lang" data-en>Images</p><p class="stat-value" id="stat-images">—</p></article>
      <article class="stat"><p class="stat-label" data-zh>平均优先级分数</p><p class="stat-label hidden-lang" data-en>Mean priority score</p><p class="stat-value" id="stat-mean">—</p></article>
      <article class="stat"><p class="stat-label" data-zh>最高优先级分数</p><p class="stat-label hidden-lang" data-en>Maximum priority score</p><p class="stat-value" id="stat-maximum">—</p></article>
      <article class="stat"><p class="stat-label" data-zh>中等及以上复核</p><p class="stat-label hidden-lang" data-en>Moderate or higher</p><p class="stat-value" id="stat-review">—</p></article>
    </section>

    <section class="distributions" aria-label="Distributions">
      <article class="section distribution">
        <h2 class="section-title" data-zh>维护优先级分布</h2><h2 class="section-title hidden-lang" data-en>Priority distribution</h2>
        <div id="risk-distribution"></div>
      </article>
      <article class="section distribution">
        <h2 class="section-title" data-zh>证据质量分布</h2><h2 class="section-title hidden-lang" data-en>Evidence-quality distribution</h2>
        <div id="evidence-distribution"></div>
      </article>
    </section>

    <section class="section explorer" aria-label="Risk result explorer">
      <div class="controls">
        <div class="field">
          <label for="search"><span data-zh>搜索文件名</span><span data-en class="hidden-lang">Search filename</span></label>
          <input id="search" type="search" autocomplete="off" placeholder="China_MotorBike_...">
        </div>
        <div class="field">
          <label for="risk-filter"><span data-zh>优先级</span><span data-en class="hidden-lang">Priority</span></label>
          <select id="risk-filter"><option value="all">全部 / All</option><option value="low">Low</option><option value="moderate">Moderate</option><option value="high">High</option><option value="critical">Critical</option></select>
        </div>
        <div class="field">
          <label for="evidence-filter"><span data-zh>证据质量</span><span data-en class="hidden-lang">Evidence</span></label>
          <select id="evidence-filter"><option value="all">全部 / All</option><option value="not_applicable">N/A</option><option value="low">Low</option><option value="moderate">Moderate</option><option value="high">High</option></select>
        </div>
        <div class="field">
          <label for="sort"><span data-zh>排序</span><span data-en class="hidden-lang">Sort</span></label>
          <select id="sort"><option value="priority">优先级高到低 / Priority</option><option value="filename">文件名 / Filename</option><option value="confidence">平均置信度 / Confidence</option></select>
        </div>
      </div>

      <div class="explorer-body">
        <aside class="detail" aria-live="polite">
          <div class="image-frame">
            <img id="detail-image" alt="">
            <p id="image-fallback" class="image-fallback"><span data-zh>标注图片无法加载</span><span data-en class="hidden-lang">Annotated image could not be loaded</span></p>
          </div>
          <div class="detail-head"><h2 id="detail-name" class="detail-name">—</h2><span id="detail-score" class="score-pill">—</span></div>
          <div class="detail-meta">
            <span id="detail-level">—</span><span id="detail-evidence">—</span><span id="detail-confidence">—</span><span id="detail-detections">—</span>
          </div>
          <p id="detail-recommendation" class="recommendation">—</p>
          <div id="detail-flags" class="flags"></div>
          <div id="class-list" class="class-list"></div>
        </aside>

        <div class="table-area">
          <div class="table-summary"><span id="result-count">—</span><span data-zh>选择文件查看详情</span><span data-en class="hidden-lang">Select a file for details</span></div>
          <div class="table-wrap">
            <table>
              <thead><tr><th class="num">#</th><th><span data-zh>文件</span><span data-en class="hidden-lang">File</span></th><th class="num"><span data-zh>分数</span><span data-en class="hidden-lang">Score</span></th><th><span data-zh>优先级</span><span data-en class="hidden-lang">Priority</span></th><th><span data-zh>证据</span><span data-en class="hidden-lang">Evidence</span></th><th class="num"><span data-zh>检测数</span><span data-en class="hidden-lang">Detections</span></th></tr></thead>
              <tbody id="result-body"></tbody>
            </table>
          </div>
          <p id="empty-results" class="empty"><span data-zh>没有符合当前筛选条件的结果。</span><span data-en class="hidden-lang">No results match the current filters.</span></p>
        </div>
      </div>
    </section>
  </main>

  <footer class="shell">
    <div class="footer-line"><span id="footer-identity"></span><span id="footer-time"></span><span>report-v0.3.0</span></div>
  </footer>

  <script id="report-data" type="application/json">__REPORT_DATA__</script>
  <script>
    (() => {
      const report = JSON.parse(document.getElementById("report-data").textContent);
      const items = report.items;
      let language = "zh";
      let selectedName = items.length ? items[0].source_prediction : null;

      const labels = {
        zh: {
          low: "低", moderate: "中等", high: "高", critical: "严重",
          not_applicable: "不适用", evidence: "证据", mean: "平均", minimum: "最低",
          detections: "个检测", results: "个结果", contribution: "贡献", count: "数量", coverage: "覆盖"
        },
        en: {
          low: "Low", moderate: "Moderate", high: "High", critical: "Critical",
          not_applicable: "N/A", evidence: "Evidence", mean: "mean", minimum: "minimum",
          detections: "detections", results: "results", contribution: "contribution", count: "count", coverage: "coverage"
        }
      };

      const byId = (id) => document.getElementById(id);
      const t = (key) => labels[language][key] || key;
      const number = (value, digits = 1) => value === null || value === undefined ? "—" : Number(value).toFixed(digits);

      function applyLanguage() {
        document.documentElement.lang = language === "zh" ? "zh-CN" : "en";
        document.querySelectorAll("[data-zh]").forEach((element) => element.classList.toggle("hidden-lang", language !== "zh"));
        document.querySelectorAll("[data-en]").forEach((element) => element.classList.toggle("hidden-lang", language !== "en"));
        byId("language-button").textContent = language === "zh" ? "English" : "中文";
        renderDistributions();
        renderTable();
        renderDetail();
      }

      function makeBar(container, key, count, total) {
        const row = document.createElement("div");
        row.className = "bar-row";
        const name = document.createElement("span");
        name.className = "bar-label";
        name.textContent = t(key);
        const track = document.createElement("div");
        track.className = "bar-track";
        const fill = document.createElement("div");
        fill.className = `bar-fill tone-${key}`;
        fill.style.width = `${total ? (count / total) * 100 : 0}%`;
        track.appendChild(fill);
        const value = document.createElement("span");
        value.className = "bar-value";
        value.textContent = String(count);
        row.append(name, track, value);
        container.appendChild(row);
      }

      function renderDistributions() {
        const total = report.summary.file_count;
        const risk = byId("risk-distribution");
        const evidence = byId("evidence-distribution");
        risk.replaceChildren();
        evidence.replaceChildren();
        ["low", "moderate", "high", "critical"].forEach((key) => makeBar(risk, key, report.summary.risk_level_counts[key], total));
        ["not_applicable", "low", "moderate", "high"].forEach((key) => makeBar(evidence, key, report.summary.evidence_quality_counts[key], total));
      }

      function visibleItems() {
        const query = byId("search").value.trim().toLowerCase();
        const risk = byId("risk-filter").value;
        const evidence = byId("evidence-filter").value;
        const sort = byId("sort").value;
        const filtered = items.filter((item) =>
          (!query || item.source_prediction.toLowerCase().includes(query)) &&
          (risk === "all" || item.risk_level === risk) &&
          (evidence === "all" || item.evidence_quality === evidence)
        );
        return [...filtered].sort((left, right) => {
          if (sort === "filename") return left.source_prediction.localeCompare(right.source_prediction);
          if (sort === "confidence") return (right.mean_confidence ?? -1) - (left.mean_confidence ?? -1) || left.source_prediction.localeCompare(right.source_prediction);
          return right.risk_score - left.risk_score || left.source_prediction.localeCompare(right.source_prediction);
        });
      }

      function badge(value) {
        const span = document.createElement("span");
        span.className = `badge badge-${value}`;
        span.textContent = t(value);
        return span;
      }

      function renderTable() {
        const visible = visibleItems();
        const body = byId("result-body");
        body.replaceChildren();
        byId("result-count").textContent = `${visible.length} ${t("results")}`;
        byId("empty-results").style.display = visible.length ? "none" : "block";
        if (visible.length && !visible.some((item) => item.source_prediction === selectedName)) {
          selectedName = visible[0].source_prediction;
        }
        visible.forEach((item) => {
          const row = document.createElement("tr");
          if (item.source_prediction === selectedName) row.classList.add("selected");
          const rank = document.createElement("td");
          rank.className = "num";
          rank.textContent = String(item.rank);
          const file = document.createElement("td");
          const choose = document.createElement("button");
          choose.type = "button";
          choose.className = "select-row";
          choose.textContent = item.source_prediction;
          choose.addEventListener("click", () => { selectedName = item.source_prediction; renderTable(); renderDetail(); });
          file.appendChild(choose);
          const score = document.createElement("td");
          score.className = "num";
          score.textContent = number(item.risk_score);
          const level = document.createElement("td");
          level.appendChild(badge(item.risk_level));
          const evidence = document.createElement("td");
          evidence.appendChild(badge(item.evidence_quality));
          const detections = document.createElement("td");
          detections.className = "num";
          detections.textContent = String(item.detection_count);
          row.append(rank, file, score, level, evidence, detections);
          body.appendChild(row);
        });
      }

      function renderDetail() {
        const item = items.find((candidate) => candidate.source_prediction === selectedName);
        if (!item) return;
        const image = byId("detail-image");
        const fallback = byId("image-fallback");
        image.style.display = "block";
        fallback.style.display = "none";
        image.src = item.annotated_image;
        image.alt = language === "zh" ? `${item.source_prediction} 标注图片` : `Annotated ${item.source_prediction}`;
        image.onerror = () => { image.style.display = "none"; fallback.style.display = "block"; };
        byId("detail-name").textContent = item.source_prediction;
        byId("detail-score").textContent = number(item.risk_score);
        byId("detail-level").textContent = `${language === "zh" ? "优先级" : "Priority"}: ${t(item.risk_level)}`;
        byId("detail-evidence").textContent = `${t("evidence")}: ${t(item.evidence_quality)}`;
        byId("detail-confidence").textContent = `${t("mean")} ${number(item.mean_confidence, 3)} · ${t("minimum")} ${number(item.minimum_confidence, 3)}`;
        byId("detail-detections").textContent = `${item.detection_count} ${t("detections")}`;
        byId("detail-recommendation").textContent = item.recommendation[language];
        const flags = byId("detail-flags");
        flags.replaceChildren();
        item.flags.forEach((flag) => {
          const line = document.createElement("p");
          line.className = "flag";
          line.textContent = `⚑ ${flag[language]}`;
          flags.appendChild(line);
        });
        const classList = byId("class-list");
        classList.replaceChildren();
        item.classes.forEach((classItem) => {
          const row = document.createElement("div");
          row.className = "class-row";
          const line = document.createElement("div");
          line.className = "class-line";
          const name = document.createElement("strong");
          name.textContent = `${classItem.code} · ${language === "zh" ? classItem.name_zh : classItem.name_en}`;
          const values = document.createElement("span");
          values.textContent = `${t("count")} ${classItem.count} · ${t("coverage")} ${(classItem.coverage_ratio * 100).toFixed(2)}% · ${t("contribution")} ${number(classItem.score_contribution)}`;
          line.append(name, values);
          const track = document.createElement("div");
          track.className = "class-track";
          const fill = document.createElement("div");
          fill.className = "class-fill";
          fill.style.width = `${Math.min(100, (classItem.score_contribution / classItem.maximum_points) * 100)}%`;
          track.appendChild(fill);
          row.append(line, track);
          classList.appendChild(row);
        });
      }

      byId("stat-images").textContent = String(report.summary.file_count);
      byId("stat-mean").textContent = number(report.summary.score_statistics.mean);
      byId("stat-maximum").textContent = number(report.summary.score_statistics.maximum);
      byId("stat-review").textContent = String(report.summary.risk_level_counts.moderate + report.summary.risk_level_counts.high + report.summary.risk_level_counts.critical);
      byId("footer-identity").textContent = `${report.run_name} / ${report.prediction_name} / ${report.risk_name}`;
      byId("footer-time").textContent = report.generated_at_utc;
      byId("language-button").addEventListener("click", () => { language = language === "zh" ? "en" : "zh"; applyLanguage(); });
      ["search", "risk-filter", "evidence-filter", "sort"].forEach((id) => byId(id).addEventListener(id === "search" ? "input" : "change", () => { renderTable(); renderDetail(); }));
      renderDistributions();
      renderTable();
      renderDetail();
    })();
  </script>
</body>
</html>
"""


def render_dashboard(payload: dict[str, Any]) -> str:
    """Render one offline HTML document with no external resources."""
    serialized = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    serialized = serialized.replace("&", "\\u0026").replace("<", "\\u003c").replace(">", "\\u003e")
    return _TEMPLATE.replace("__REPORT_DATA__", serialized)
