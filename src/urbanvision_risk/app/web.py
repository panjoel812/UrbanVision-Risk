# ruff: noqa: E501
"""Self-contained local web interface / 自包含本地网页界面。"""

APP_HTML = """<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>UrbanVision-Risk · Local Inspection</title>
  <style>
    :root {
      color-scheme: light;
      --ink: #17231f;
      --muted: #68736e;
      --paper: #f2f4ef;
      --card: #ffffff;
      --soft: #e7ece7;
      --line: #d5ddd7;
      --forest: #174f3e;
      --forest-2: #24745a;
      --mint: #d9ece3;
      --amber: #c4862c;
      --orange: #c45d36;
      --red: #963c45;
      --shadow: 0 22px 60px rgba(27, 50, 41, 0.10);
    }
    @media (prefers-color-scheme: dark) {
      :root {
        color-scheme: dark;
        --ink: #eef5f1;
        --muted: #aab7b0;
        --paper: #101713;
        --card: #19221d;
        --soft: #253029;
        --line: #34433a;
        --forest: #8ac6a9;
        --forest-2: #66b58e;
        --mint: #263e33;
        --amber: #dfb35d;
        --orange: #e4865f;
        --red: #df7d87;
        --shadow: 0 22px 60px rgba(0, 0, 0, 0.26);
      }
    }
    * { box-sizing: border-box; }
    html { scroll-behavior: smooth; }
    body {
      margin: 0;
      background:
        radial-gradient(circle at 6% 3%, color-mix(in srgb, var(--forest-2) 13%, transparent), transparent 26rem),
        var(--paper);
      color: var(--ink);
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      line-height: 1.5;
    }
    button, input { font: inherit; }
    button:focus-visible, input:focus-visible, .upload-zone:focus-within {
      outline: 3px solid color-mix(in srgb, var(--forest-2) 48%, transparent);
      outline-offset: 3px;
    }
    .hidden-lang, .hidden { display: none !important; }
    .shell { width: min(1240px, calc(100% - 32px)); margin-inline: auto; }
    header { padding: 26px 0 18px; }
    .nav { display: flex; justify-content: space-between; gap: 20px; align-items: center; }
    .brand { display: flex; align-items: center; gap: 11px; font-weight: 780; letter-spacing: -0.02em; }
    .brand-mark { width: 34px; height: 34px; display: grid; place-items: center; border-radius: 11px; color: #fff; background: var(--forest); box-shadow: var(--shadow); }
    .nav-actions { display: flex; align-items: center; gap: 9px; }
    .local-chip, .language-button, .metrology-link { border: 1px solid var(--line); border-radius: 999px; background: var(--card); color: var(--ink); }
    .local-chip { display: flex; align-items: center; gap: 7px; padding: 7px 11px; font-size: .76rem; color: var(--muted); }
    .status-dot { width: 8px; height: 8px; border-radius: 50%; background: var(--amber); }
    .status-dot.ready { background: var(--forest-2); box-shadow: 0 0 0 4px color-mix(in srgb, var(--forest-2) 15%, transparent); }
    .language-button { padding: 7px 12px; cursor: pointer; }
    .metrology-link { padding: 7px 12px; color: var(--forest); font-size: .76rem; font-weight: 720; text-decoration: none; }
    .hero { padding: 34px 0 30px; display: grid; grid-template-columns: minmax(0, 1.3fr) minmax(280px, .7fr); gap: 28px; align-items: end; }
    .eyebrow { margin: 0 0 9px; color: var(--forest); font-size: .78rem; font-weight: 750; letter-spacing: .13em; text-transform: uppercase; }
    h1 { margin: 0; max-width: 820px; font-size: clamp(2.15rem, 4.4vw, 4.05rem); line-height: .98; letter-spacing: -.055em; }
    .hero-copy { margin: 17px 0 0; max-width: 720px; color: var(--muted); font-size: clamp(.98rem, 1.4vw, 1.12rem); }
    .safety { padding: 15px 16px; border: 1px solid color-mix(in srgb, var(--amber) 45%, var(--line)); border-radius: 15px; background: color-mix(in srgb, var(--amber) 9%, var(--card)); font-size: .82rem; }
    .safety strong { color: var(--amber); }
    main { padding-bottom: 64px; }
    .workspace { display: grid; grid-template-columns: minmax(300px, .72fr) minmax(0, 1.28fr); gap: 18px; align-items: start; }
    .card { background: var(--card); border: 1px solid var(--line); border-radius: 20px; box-shadow: var(--shadow); }
    .input-card { padding: 19px; position: sticky; top: 16px; }
    .card-heading { display: flex; align-items: flex-start; justify-content: space-between; gap: 14px; margin-bottom: 15px; }
    h2, h3 { margin: 0; letter-spacing: -.025em; }
    h2 { font-size: 1.08rem; }
    h3 { font-size: .92rem; }
    .step { flex: none; padding: 3px 8px; border-radius: 999px; background: var(--mint); color: var(--forest); font-size: .68rem; font-weight: 700; }
    .upload-zone { position: relative; display: grid; place-items: center; min-height: 260px; overflow: hidden; border: 1.5px dashed color-mix(in srgb, var(--forest) 48%, var(--line)); border-radius: 16px; background: var(--soft); transition: border-color 160ms, transform 160ms; }
    .upload-zone.dragging { border-color: var(--forest-2); transform: translateY(-2px); }
    .upload-zone input { position: absolute; inset: 0; width: 100%; height: 100%; opacity: 0; cursor: pointer; }
    .upload-prompt { padding: 28px; text-align: center; pointer-events: none; }
    .upload-icon { width: 54px; height: 54px; margin: 0 auto 14px; display: grid; place-items: center; border-radius: 16px; background: var(--card); color: var(--forest); font-size: 1.45rem; box-shadow: 0 10px 24px rgba(26, 73, 55, .09); }
    .upload-title { margin: 0; font-weight: 700; }
    .upload-help { margin: 7px 0 0; color: var(--muted); font-size: .78rem; }
    .preview { position: absolute; inset: 0; width: 100%; height: 100%; object-fit: contain; background: #111; pointer-events: none; }
    .file-row { min-height: 44px; display: flex; align-items: center; justify-content: space-between; gap: 12px; padding: 11px 2px 2px; font-size: .76rem; color: var(--muted); }
    .file-name { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
    .analyze-button { width: 100%; margin-top: 12px; border: 0; border-radius: 13px; padding: 12px 16px; background: var(--forest); color: #fff; font-weight: 720; cursor: pointer; transition: transform 140ms, opacity 140ms; }
    .analyze-button:not(:disabled):hover { transform: translateY(-1px); }
    .analyze-button:disabled { cursor: not-allowed; opacity: .42; }
    .privacy-note { margin: 12px 0 0; display: flex; gap: 8px; color: var(--muted); font-size: .72rem; }
    .app-status { margin: 12px 0 0; min-height: 21px; color: var(--muted); font-size: .78rem; }
    .app-status.error { color: var(--red); }
    .result-placeholder { min-height: 580px; display: grid; place-items: center; padding: 42px; text-align: center; color: var(--muted); }
    .placeholder-graphic { width: 112px; height: 112px; margin: 0 auto 18px; display: grid; place-items: center; border-radius: 32px; background: var(--soft); color: var(--forest); font-size: 2.4rem; transform: rotate(-4deg); }
    .placeholder-title { color: var(--ink); font-weight: 720; }
    .result { display: grid; gap: 18px; }
    .result-top { padding: 18px; display: grid; grid-template-columns: minmax(0, 1.4fr) minmax(235px, .6fr); gap: 18px; }
    .annotated-frame { min-height: 360px; display: grid; place-items: center; overflow: hidden; border-radius: 15px; background: #0e1311; }
    .annotated-frame img { width: 100%; height: 100%; max-height: 610px; object-fit: contain; }
    .score-panel { padding: 8px 5px; display: flex; flex-direction: column; align-items: center; justify-content: center; text-align: center; }
    .score-ring { --score-angle: 0deg; width: 154px; height: 154px; display: grid; place-items: center; border-radius: 50%; background: conic-gradient(var(--forest-2) var(--score-angle), var(--soft) 0); position: relative; }
    .score-ring::after { content: ""; position: absolute; inset: 13px; border-radius: 50%; background: var(--card); }
    .score-content { z-index: 1; }
    .score-value { display: block; font-size: 2.55rem; line-height: 1; font-weight: 780; letter-spacing: -.06em; }
    .score-unit { color: var(--muted); font-size: .7rem; }
    .badges { display: flex; flex-wrap: wrap; justify-content: center; gap: 7px; margin-top: 15px; }
    .badge { padding: 4px 8px; border: 1px solid currentColor; border-radius: 999px; font-size: .7rem; font-weight: 700; }
    .badge-low { color: var(--forest-2); }
    .badge-moderate { color: var(--amber); }
    .badge-high { color: var(--orange); }
    .badge-critical { color: var(--red); }
    .badge-review_required { color: var(--orange); }
    .badge-not_applicable { color: var(--muted); }
    .recommendation { width: 100%; margin: 16px 0 0; padding: 12px; border-radius: 12px; background: var(--mint); text-align: left; font-size: .8rem; }
    .result-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 18px; }
    .section-card { padding: 18px; }
    .section-subtitle { margin: 4px 0 15px; color: var(--muted); font-size: .74rem; }
    .class-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 9px; }
    .class-card { padding: 11px; border: 1px solid var(--line); border-radius: 12px; background: var(--soft); }
    .class-code { color: var(--forest); font-size: .7rem; font-weight: 760; }
    .class-line { display: flex; align-items: end; justify-content: space-between; gap: 10px; margin-top: 3px; }
    .class-name { font-size: .76rem; }
    .class-count { font-size: 1.35rem; font-weight: 780; }
    .contribution-list { display: grid; gap: 12px; }
    .contribution-head { display: flex; justify-content: space-between; gap: 12px; font-size: .74rem; }
    .contribution-meta { color: var(--muted); }
    .bar { height: 7px; overflow: hidden; margin-top: 6px; border-radius: 999px; background: var(--soft); }
    .bar-fill { height: 100%; border-radius: inherit; background: var(--forest-2); }
    .evidence-line { display: flex; justify-content: space-between; gap: 12px; padding: 9px 0; border-bottom: 1px solid var(--line); font-size: .78rem; }
    .evidence-line:last-child { border-bottom: 0; }
    .evidence-label { color: var(--muted); }
    .flags { display: grid; gap: 7px; margin-top: 12px; }
    .flag { margin: 0; padding: 8px 10px; border-radius: 9px; color: var(--orange); background: color-mix(in srgb, var(--orange) 9%, transparent); font-size: .74rem; }
    .narrative-card { display: grid; gap: 14px; }
    .narrative-heading { display: flex; align-items: flex-start; justify-content: space-between; gap: 16px; }
    .narrative-button { flex: none; border: 0; border-radius: 11px; padding: 9px 13px; background: var(--forest); color: #fff; font-size: .74rem; font-weight: 720; cursor: pointer; }
    .narrative-button:disabled { cursor: not-allowed; opacity: .45; }
    .narrative-content { display: grid; gap: 13px; }
    .narrative-summary { margin: 0; padding: 13px 14px; border-radius: 12px; background: var(--mint); font-size: .82rem; }
    .narrative-columns { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }
    .narrative-block { padding: 13px 14px; border: 1px solid var(--line); border-radius: 12px; background: var(--soft); }
    .narrative-block h4 { margin: 0 0 8px; font-size: .78rem; }
    .narrative-list { margin: 0; padding-left: 18px; color: var(--muted); font-size: .76rem; }
    .narrative-list li + li { margin-top: 6px; }
    .narrative-limitation { margin: 0; color: var(--muted); font-size: .72rem; }
    .table-card { overflow: hidden; }
    .table-heading { padding: 18px 18px 12px; }
    .table-wrap { overflow-x: auto; }
    table { width: 100%; border-collapse: collapse; font-size: .76rem; }
    th, td { padding: 10px 13px; border-top: 1px solid var(--line); text-align: left; }
    th { color: var(--muted); font-size: .68rem; }
    td.num, th.num { text-align: right; font-variant-numeric: tabular-nums; }
    .empty-row { padding: 18px; color: var(--muted); text-align: center; font-size: .78rem; }
    .result-footer { padding: 12px 16px; border-left: 4px solid var(--amber); border-radius: 0 12px 12px 0; background: color-mix(in srgb, var(--amber) 8%, var(--card)); color: var(--muted); font-size: .72rem; }
    footer { padding: 0 0 34px; color: var(--muted); font-size: .7rem; }
    @media (max-width: 900px) {
      .hero, .workspace { grid-template-columns: 1fr; }
      .input-card { position: static; }
      .result-top { grid-template-columns: 1fr; }
      .score-panel { padding: 12px; }
    }
    @media (max-width: 620px) {
      .shell { width: min(100% - 20px, 1240px); }
      header { padding-top: 16px; }
      .local-chip span:last-child { display: none; }
      .hero { padding-top: 23px; }
      .safety { margin-top: 4px; }
      .upload-zone { min-height: 225px; }
      .result-placeholder { min-height: 420px; }
      .result-grid, .class-grid, .narrative-columns { grid-template-columns: 1fr; }
      .result-top, .section-card { padding: 14px; }
      .annotated-frame { min-height: 260px; }
    }
    @media (prefers-reduced-motion: reduce) {
      *, *::before, *::after { scroll-behavior: auto !important; transition: none !important; }
    }
  </style>
</head>
<body>
  <header class="shell">
    <nav class="nav" aria-label="Primary">
      <div class="brand"><span class="brand-mark" aria-hidden="true">UV</span><span>UrbanVision-Risk</span></div>
      <div class="nav-actions">
        <div class="local-chip"><span id="status-dot" class="status-dot"></span><span id="model-status"><span data-zh>正在检查本地模型</span><span data-en class="hidden-lang">Checking local model</span></span></div>
        <a class="metrology-link" href="/metrology"><span data-zh>精密量测</span><span data-en class="hidden-lang">Precision Lab</span></a>
        <button id="language-button" class="language-button" type="button" aria-label="Switch language">English</button>
      </div>
    </nav>
    <section class="hero">
      <div>
        <p class="eyebrow">Reliability console · UrbanVision v3.1</p>
        <h1><span data-zh>道路缺陷，<br>从检测到可靠性证据。</span><span data-en class="hidden-lang">Road damage,<br>from detection to reliability evidence.</span></h1>
        <p class="hero-copy"><span data-zh>三视图共识、定位稳定性、不确定性量化、主动学习优先级和本地 AI 说明全部在这台 Mac 上完成。</span><span data-en class="hidden-lang">Three-view consensus, localization stability, uncertainty, active-learning priority, and local AI narrative all run on this Mac.</span></p>
      </div>
      <div class="safety" role="note"><strong><span data-zh>重要边界:</span><span data-en class="hidden-lang">Important boundary: </span></strong><span data-zh>这是维护复核优先级，不是道路安全判定；最终检查、封闭和维修必须由人决定。</span><span data-en class="hidden-lang">This is a maintenance-review priority, not a road-safety verdict; humans make final inspection, closure, and repair decisions.</span></div>
    </section>
  </header>

  <main class="shell">
    <div class="workspace">
      <section class="card input-card" aria-labelledby="upload-heading">
        <div class="card-heading"><h2 id="upload-heading"><span data-zh>选择道路图片</span><span data-en class="hidden-lang">Choose a road image</span></h2><span class="step">01 · INPUT</span></div>
        <label id="upload-zone" class="upload-zone">
          <input id="image-input" type="file" accept="image/jpeg,image/png,image/webp">
          <div id="upload-prompt" class="upload-prompt">
            <div class="upload-icon" aria-hidden="true">+</div>
            <p class="upload-title"><span data-zh>点击选择或拖入图片</span><span data-en class="hidden-lang">Click or drop an image</span></p>
            <p class="upload-help">JPEG · PNG · WebP · ≤ 15 MiB · ≤ 40 MP</p>
          </div>
          <img id="preview" class="preview hidden" alt="Local preview">
        </label>
        <div class="file-row"><span id="file-name" class="file-name"><span data-zh>尚未选择文件</span><span data-en class="hidden-lang">No file selected</span></span><span id="file-size">—</span></div>
        <button id="analyze-button" class="analyze-button" type="button" disabled><span data-zh>开始本地巡检</span><span data-en class="hidden-lang">Run local inspection</span></button>
        <p class="privacy-note"><span aria-hidden="true">⌂</span><span data-zh>图片只发送到本机 127.0.0.1，不会上传到互联网。</span><span data-en class="hidden-lang">The image is sent only to local 127.0.0.1, never to the internet.</span></p>
        <p id="app-status" class="app-status" aria-live="polite"></p>
      </section>

      <section aria-live="polite">
        <div id="placeholder" class="card result-placeholder">
          <div><div class="placeholder-graphic" aria-hidden="true">⌁</div><p class="placeholder-title"><span data-zh>结果将在这里出现</span><span data-en class="hidden-lang">Your result will appear here</span></p><p><span data-zh>选择图片并运行后，你会看到检测框、风险分数、类别贡献和人工复核建议。</span><span data-en class="hidden-lang">After running, you will see detections, priority score, class contributions, and a human-review recommendation.</span></p></div>
        </div>

        <div id="result" class="result hidden">
          <section class="card result-top">
            <div class="annotated-frame"><img id="annotated-image" alt="Annotated road inspection"></div>
            <div class="score-panel">
              <div id="score-ring" class="score-ring"><div class="score-content"><span id="score-value" class="score-value">—</span><span class="score-unit">/ 100</span></div></div>
              <div class="badges"><span id="risk-badge" class="badge">—</span><span id="evidence-badge" class="badge">—</span></div>
              <p id="recommendation" class="recommendation">—</p>
            </div>
          </section>

          <div class="result-grid">
            <section class="card section-card"><h3><span data-zh>检测与观察统计</span><span data-en class="hidden-lang">Detections and observations</span></h3><p class="section-subtitle" id="image-meta">—</p><div id="class-grid" class="class-grid"></div></section>
            <section class="card section-card"><h3><span data-zh>分数贡献</span><span data-en class="hidden-lang">Score contributions</span></h3><p class="section-subtitle"><span data-zh>每类对 0-100 维护优先级的贡献</span><span data-en class="hidden-lang">Each class contribution to the 0-100 maintenance priority</span></p><div id="contribution-list" class="contribution-list"></div></section>
            <section class="card section-card"><h3><span data-zh>证据质量</span><span data-en class="hidden-lang">Evidence quality</span></h3><p class="section-subtitle"><span data-zh>置信度描述证据，不改变风险分数</span><span data-en class="hidden-lang">Confidence describes evidence; it never changes the score</span></p><div id="evidence-details"></div><div id="flags" class="flags"></div></section>
            <section class="card section-card"><h3><span data-zh>多视图模型可靠性</span><span data-en class="hidden-lang">Multi-view model reliability</span></h3><p id="reliability-method" class="section-subtitle">—</p><div id="reliability-details"></div><div id="reliability-alert" class="flags"></div></section>
            <section class="card section-card"><h3><span data-zh>巡检记录</span><span data-en class="hidden-lang">Inspection record</span></h3><p class="section-subtitle"><span data-zh>结果已在本机保存且不会覆盖</span><span data-en class="hidden-lang">Saved locally without overwriting prior results</span></p><div class="evidence-line"><span class="evidence-label">ID</span><strong id="inspection-id">—</strong></div><div class="evidence-line"><span class="evidence-label"><span data-zh>源文件</span><span data-en class="hidden-lang">Source file</span></span><strong id="source-file">—</strong></div><div class="evidence-line"><span class="evidence-label"><span data-zh>生成时间</span><span data-en class="hidden-lang">Created</span></span><strong id="created-time">—</strong></div></section>
          </div>

          <section class="card section-card narrative-card">
            <div class="narrative-heading">
              <div><h3><span data-zh>本地 AI 巡检说明</span><span data-en class="hidden-lang">Local AI inspection narrative</span></h3><p id="narrative-meta" class="section-subtitle"><span data-zh>只使用结构化检测结果；不会发送图片、文件名或云端请求。</span><span data-en class="hidden-lang">Uses structured detections only; no image, filename, or cloud request is sent.</span></p></div>
              <button id="narrative-button" class="narrative-button" type="button" disabled><span data-zh>生成本地说明</span><span data-en class="hidden-lang">Generate locally</span></button>
            </div>
            <div id="narrative-content" class="narrative-content hidden">
              <p id="narrative-summary" class="narrative-summary">—</p>
              <div class="narrative-columns">
                <div class="narrative-block"><h4><span data-zh>结构化观察</span><span data-en class="hidden-lang">Structured observations</span></h4><ul id="narrative-observations" class="narrative-list"></ul></div>
                <div class="narrative-block"><h4><span data-zh>人工复核动作</span><span data-en class="hidden-lang">Human-review actions</span></h4><ul id="narrative-actions" class="narrative-list"></ul></div>
              </div>
              <p id="narrative-limitation" class="narrative-limitation">—</p>
            </div>
          </section>

          <section class="card table-card"><div class="table-heading"><h3><span data-zh>检测明细</span><span data-en class="hidden-lang">Detection details</span></h3><p id="detection-summary" class="section-subtitle">—</p></div><div class="table-wrap"><table><thead><tr><th>#</th><th><span data-zh>类别</span><span data-en class="hidden-lang">Class</span></th><th class="num"><span data-zh>置信度</span><span data-en class="hidden-lang">Confidence</span></th><th><span data-zh>边界框 (x1, y1, x2, y2)</span><span data-en class="hidden-lang">Box (x1, y1, x2, y2)</span></th></tr></thead><tbody id="detection-body"></tbody></table></div><p id="empty-detections" class="empty-row hidden"><span data-zh>模型没有返回检测框；这不代表道路无缺陷，必须人工复核。</span><span data-en class="hidden-lang">The model returned no boxes; this does not prove the road is defect-free and requires human review.</span></p></section>
          <div class="result-footer"><strong><span data-zh>安全说明:</span><span data-en class="hidden-lang">Safety note: </span></strong><span id="limitation">—</span></div>
        </div>
      </section>
    </div>
  </main>
  <footer class="shell"><span>UrbanVision-Risk v3.1 · Reliability + Metrology · Fully local / 完全本地</span></footer>

  <script>
    (() => {
      let language = "zh";
      let selectedFile = null;
      let previewUrl = null;
      let latestResult = null;
      let latestNarrative = null;
      let modelState = "checking";
      const byId = (id) => document.getElementById(id);
      const labels = {
        zh: { low: "低优先级", moderate: "中等优先级", high: "高优先级", critical: "严重优先级", review_required: "需要人工复核", not_applicable: "证据不适用", evidence: "证据", checking: "正在检查本地模型", ready: "本地模型就绪", unavailable: "本地服务未连接", analyzing: "正在通过 MPS 运行三视图共识与可靠性分析…", complete: "巡检完成，结果已保存在本机。", detections: "个检测", mean: "平均置信度", minimum: "最低置信度", count: "数量", coverage: "覆盖率", points: "贡献", auxiliary: "辅助观察，不参与评分", narrative_ready: "可以生成本地双语说明。", narrative_loading: "正在通过本地 Ollama 或审计模板生成说明…", narrative_template: "审计模板 · 完全本地", narrative_ollama: "Ollama 本地模型", narrative_error: "本地说明生成失败，请检查终端日志。" },
        en: { low: "Low priority", moderate: "Moderate priority", high: "High priority", critical: "Critical priority", review_required: "Human review required", not_applicable: "Evidence N/A", evidence: "Evidence", checking: "Checking local model", ready: "Local model ready", unavailable: "Local service unavailable", analyzing: "Running three-view MPS consensus and reliability analysis…", complete: "Inspection complete and saved locally.", detections: "detections", mean: "Mean confidence", minimum: "Minimum confidence", count: "count", coverage: "coverage", points: "contribution", auxiliary: "Auxiliary observation; not scored", narrative_ready: "Ready to generate a local bilingual narrative.", narrative_loading: "Generating through local Ollama or the audited template…", narrative_template: "Audited template · fully local", narrative_ollama: "Local Ollama model", narrative_error: "Local narrative generation failed; check the terminal log." }
      };
      const qualityLabels = {
        zh: { not_applicable: "不适用", low: "低", moderate: "中等", high: "高" },
        en: { not_applicable: "N/A", low: "Low", moderate: "Moderate", high: "High" }
      };
      const t = (key) => labels[language][key] || key;
      const number = (value, digits = 1) => value === null || value === undefined ? "—" : Number(value).toFixed(digits);

      function applyLanguage() {
        document.documentElement.lang = language === "zh" ? "zh-CN" : "en";
        document.querySelectorAll("[data-zh]").forEach((element) => element.classList.toggle("hidden-lang", language !== "zh"));
        document.querySelectorAll("[data-en]").forEach((element) => element.classList.toggle("hidden-lang", language !== "en"));
        byId("language-button").textContent = language === "zh" ? "English" : "中文";
        byId("model-status").textContent = modelState === "ready" ? `${t("ready")} · MPS` : t(modelState);
        if (latestResult) {
          renderResult(latestResult, false);
          if (latestNarrative) renderNarrative(latestNarrative);
          setStatus(t("complete"));
        }
      }

      function setStatus(message, isError = false) {
        const status = byId("app-status");
        status.textContent = message;
        status.classList.toggle("error", isError);
      }

      function setFile(file) {
        if (!file) return;
        selectedFile = file;
        if (previewUrl) URL.revokeObjectURL(previewUrl);
        previewUrl = URL.createObjectURL(file);
        byId("preview").src = previewUrl;
        byId("preview").classList.remove("hidden");
        byId("upload-prompt").classList.add("hidden");
        byId("file-name").textContent = file.name;
        byId("file-size").textContent = `${(file.size / 1024 / 1024).toFixed(2)} MiB`;
        byId("analyze-button").disabled = false;
        setStatus("");
      }

      function makeBadge(element, value, prefix = "") {
        element.className = `badge badge-${value}`;
        element.textContent = `${prefix}${t(value)}`;
      }

      function renderResult(payload, resetNarrative = false) {
        latestResult = payload;
        const prediction = payload.prediction;
        const risk = payload.risk;
        byId("placeholder").classList.add("hidden");
        byId("result").classList.remove("hidden");
        byId("annotated-image").src = `${payload.annotated_url}?v=${encodeURIComponent(payload.inspection_id)}`;
        const reviewRequired = risk.decision_status === "review_required" || risk.review_required === true;
        byId("score-value").textContent = reviewRequired ? "—" : number(risk.risk_score);
        byId("score-ring").style.setProperty("--score-angle", `${reviewRequired ? 0 : Math.max(0, Math.min(100, risk.risk_score)) * 3.6}deg`);
        makeBadge(byId("risk-badge"), reviewRequired ? "review_required" : risk.risk_level);
        const evidenceBadge = byId("evidence-badge");
        evidenceBadge.className = `badge badge-${risk.evidence.quality}`;
        evidenceBadge.textContent = `${t("evidence")}: ${qualityLabels[language][risk.evidence.quality]}`;
        byId("recommendation").textContent = risk.recommendation[language];
        byId("limitation").textContent = risk.limitation[language];
        byId("inspection-id").textContent = payload.inspection_id;
        byId("source-file").textContent = payload.source_filename;
        byId("created-time").textContent = new Date(payload.created_at_utc).toLocaleString(language === "zh" ? "zh-CN" : "en");
        const dimensions = prediction.image_dimensions;
        byId("image-meta").textContent = `${dimensions.width} x ${dimensions.height} px · ${prediction.detections.length} ${t("detections")}`;

        const classGrid = byId("class-grid");
        classGrid.replaceChildren();
        risk.class_breakdown.forEach((item) => {
          const card = document.createElement("div"); card.className = "class-card";
          const code = document.createElement("div"); code.className = "class-code"; code.textContent = item.code;
          const line = document.createElement("div"); line.className = "class-line";
          const name = document.createElement("span"); name.className = "class-name"; name.textContent = language === "zh" ? item.name_zh : item.name_en;
          const count = document.createElement("strong"); count.className = "class-count"; count.textContent = String(item.count);
          line.append(name, count); card.append(code, line); classGrid.appendChild(card);
        });
        (risk.auxiliary_observations || []).forEach((item) => {
          const card = document.createElement("div"); card.className = "class-card";
          const code = document.createElement("div"); code.className = "class-code"; code.textContent = `${item.code} · ${t("auxiliary")}`;
          const line = document.createElement("div"); line.className = "class-line";
          const name = document.createElement("span"); name.className = "class-name"; name.textContent = language === "zh" ? item.name_zh : item.name_en;
          const count = document.createElement("strong"); count.className = "class-count"; count.textContent = String(item.count);
          line.append(name, count); card.append(code, line); classGrid.appendChild(card);
        });

        const contributionList = byId("contribution-list");
        contributionList.replaceChildren();
        risk.class_breakdown.forEach((item) => {
          const row = document.createElement("div");
          const head = document.createElement("div"); head.className = "contribution-head";
          const name = document.createElement("strong"); name.textContent = `${item.code} · ${language === "zh" ? item.name_zh : item.name_en}`;
          const meta = document.createElement("span"); meta.className = "contribution-meta"; meta.textContent = `${t("count")} ${item.count} · ${t("coverage")} ${(item.coverage_ratio * 100).toFixed(2)}% · ${t("points")} ${number(item.score_contribution)}`;
          head.append(name, meta);
          const bar = document.createElement("div"); bar.className = "bar";
          const fill = document.createElement("div"); fill.className = "bar-fill"; fill.style.width = `${Math.min(100, item.score_contribution / item.maximum_points * 100)}%`;
          bar.appendChild(fill); row.append(head, bar); contributionList.appendChild(row);
        });

        const evidenceDetails = byId("evidence-details");
        evidenceDetails.replaceChildren();
        [[t("mean"), number(risk.evidence.mean_detection_confidence, 3)], [t("minimum"), number(risk.evidence.minimum_detection_confidence, 3)]].forEach(([label, value]) => {
          const row = document.createElement("div"); row.className = "evidence-line";
          const left = document.createElement("span"); left.className = "evidence-label"; left.textContent = label;
          const right = document.createElement("strong"); right.textContent = value;
          row.append(left, right); evidenceDetails.appendChild(row);
        });
        const reliability = prediction.reliability || {};
        const reliabilitySummary = reliability.summary || {};
        const tierLabels = {
          zh: { low: "低", medium: "中", high: "高", not_applicable: "不适用" },
          en: { low: "Low", medium: "Medium", high: "High", not_applicable: "N/A" }
        };
        byId("reliability-method").textContent = reliability.method ? reliability.method[language] : "—";
        const reliabilityDetails = byId("reliability-details"); reliabilityDetails.replaceChildren();
        const reliabilityRows = language === "zh" ? [
          ["推理视图", reliability.view_count],
          ["共识 / 分歧簇", `${reliabilitySummary.accepted_cluster_count ?? "—"} / ${reliabilitySummary.disputed_cluster_count ?? "—"}`],
          ["平均定位稳定性", number(reliabilitySummary.mean_stability, 3)],
          ["平均不确定性", number(reliabilitySummary.mean_uncertainty, 3)],
          ["主动学习优先级", `${number(reliabilitySummary.active_learning_priority)} · ${tierLabels.zh[reliabilitySummary.active_learning_tier] || "—"}`]
        ] : [
          ["Inference views", reliability.view_count],
          ["Consensus / disputed", `${reliabilitySummary.accepted_cluster_count ?? "—"} / ${reliabilitySummary.disputed_cluster_count ?? "—"}`],
          ["Mean localization stability", number(reliabilitySummary.mean_stability, 3)],
          ["Mean uncertainty", number(reliabilitySummary.mean_uncertainty, 3)],
          ["Active-learning priority", `${number(reliabilitySummary.active_learning_priority)} · ${tierLabels.en[reliabilitySummary.active_learning_tier] || "—"}`]
        ];
        reliabilityRows.forEach(([label, value]) => {
          const row = document.createElement("div"); row.className = "evidence-line";
          const left = document.createElement("span"); left.className = "evidence-label"; left.textContent = label;
          const right = document.createElement("strong"); right.textContent = value ?? "—";
          row.append(left, right); reliabilityDetails.appendChild(row);
        });
        const reliabilityAlert = byId("reliability-alert"); reliabilityAlert.replaceChildren();
        if (reliabilitySummary.review_recommended) {
          const line = document.createElement("p"); line.className = "flag";
          line.textContent = language === "zh" ? "⚑ 多视图证据不稳定，已进入人工复核与主动学习队列。" : "⚑ Unstable multi-view evidence: routed to human review and the active-learning queue.";
          reliabilityAlert.appendChild(line);
        }
        const flags = byId("flags"); flags.replaceChildren();
        risk.audit_flags.forEach((item) => { const line = document.createElement("p"); line.className = "flag"; line.textContent = `⚑ ${item[language]}`; flags.appendChild(line); });

        const body = byId("detection-body"); body.replaceChildren();
        byId("detection-summary").textContent = `${prediction.detections.length} ${t("detections")}`;
        byId("empty-detections").classList.toggle("hidden", prediction.detections.length !== 0);
        prediction.detections.forEach((item, index) => {
          const row = document.createElement("tr");
          const indexCell = document.createElement("td"); indexCell.textContent = String(index + 1);
          const classCell = document.createElement("td"); classCell.textContent = `${item.code} · ${language === "zh" ? item.name_zh : item.name_en}`;
          const confidenceCell = document.createElement("td"); confidenceCell.className = "num"; confidenceCell.textContent = number(item.confidence, 3);
          const boxCell = document.createElement("td"); boxCell.textContent = item.bbox_xyxy.map((value) => Math.round(value)).join(", ");
          row.append(indexCell, classCell, confidenceCell, boxCell); body.appendChild(row);
        });
        if (resetNarrative) {
          latestNarrative = null;
          byId("narrative-content").classList.add("hidden");
          byId("narrative-button").disabled = false;
          byId("narrative-meta").textContent = t("narrative_ready");
        }
      }

      function renderNarrative(payload) {
        latestNarrative = payload;
        const generator = payload.generator || {};
        byId("narrative-meta").textContent = generator.mode === "ollama" ? `${t("narrative_ollama")} · ${generator.model}` : t("narrative_template");
        byId("narrative-summary").textContent = payload.summary[language];
        [["narrative-observations", payload.observations], ["narrative-actions", payload.actions]].forEach(([id, items]) => {
          const list = byId(id); list.replaceChildren();
          items.forEach((item) => { const row = document.createElement("li"); row.textContent = item[language]; list.appendChild(row); });
        });
        byId("narrative-limitation").textContent = payload.limitation[language];
        byId("narrative-content").classList.remove("hidden");
        byId("narrative-button").disabled = true;
      }

      async function generateNarrative() {
        if (!latestResult) return;
        byId("narrative-button").disabled = true;
        byId("narrative-meta").textContent = t("narrative_loading");
        try {
          const inspectionId = encodeURIComponent(latestResult.inspection_id);
          const response = await fetch(`/api/inspections/${inspectionId}/narrative`, { method: "POST" });
          const payload = await response.json();
          if (!response.ok) throw payload.error || payload;
          renderNarrative(payload);
        } catch (error) {
          const message = error && (language === "zh" ? error.message_zh : error.message_en);
          byId("narrative-meta").textContent = message || t("narrative_error");
          byId("narrative-button").disabled = false;
        }
      }

      async function inspect() {
        if (!selectedFile) return;
        byId("analyze-button").disabled = true;
        setStatus(t("analyzing"));
        const form = new FormData(); form.append("image", selectedFile, selectedFile.name);
        try {
          const response = await fetch("/api/inspect", { method: "POST", body: form });
          const payload = await response.json();
          if (!response.ok) throw payload.error || payload;
          renderResult(payload, true);
          setStatus(t("complete"));
          byId("result").scrollIntoView({ behavior: "smooth", block: "start" });
        } catch (error) {
          const message = error && (language === "zh" ? error.message_zh : error.message_en);
          const recovery = error && (language === "zh" ? error.recovery_zh : error.recovery_en);
          setStatus([message, recovery].filter(Boolean).join(" — ") || (language === "zh" ? "巡检失败，请检查终端日志。" : "Inspection failed; check the terminal log."), true);
        } finally {
          byId("analyze-button").disabled = !selectedFile;
        }
      }

      byId("language-button").addEventListener("click", () => { language = language === "zh" ? "en" : "zh"; applyLanguage(); });
      byId("image-input").addEventListener("change", (event) => setFile(event.target.files[0]));
      byId("analyze-button").addEventListener("click", inspect);
      byId("narrative-button").addEventListener("click", generateNarrative);
      const zone = byId("upload-zone");
      ["dragenter", "dragover"].forEach((eventName) => zone.addEventListener(eventName, (event) => { event.preventDefault(); zone.classList.add("dragging"); }));
      ["dragleave", "drop"].forEach((eventName) => zone.addEventListener(eventName, (event) => { event.preventDefault(); zone.classList.remove("dragging"); }));
      zone.addEventListener("drop", (event) => setFile(event.dataTransfer.files[0]));
      fetch("/api/health").then((response) => response.json()).then((health) => {
        modelState = "ready";
        byId("status-dot").classList.add("ready");
        byId("model-status").textContent = `${t("ready")} · ${health.device.toUpperCase()}`;
      }).catch(() => { modelState = "unavailable"; byId("model-status").textContent = t("unavailable"); });
    })();
  </script>
</body>
</html>
"""
