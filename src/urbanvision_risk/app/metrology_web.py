# ruff: noqa: E501, RUF001
"""Self-contained calibrated metrology workbench / 自包含标定量测工作台。"""

METROLOGY_HTML = """<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>UrbanVision-Risk · Precision Lab</title>
  <style>
    :root {
      color-scheme: light;
      --ink: #17211d;
      --muted: #68736e;
      --paper: #eef2ed;
      --card: #ffffff;
      --soft: #e8eee9;
      --line: #d3ddd6;
      --forest: #155b46;
      --forest-2: #238363;
      --mint: #d9eee4;
      --cyan: #1f8194;
      --amber: #b87922;
      --orange: #c25a32;
      --red: #a13d4a;
      --shadow: 0 22px 60px rgba(22, 53, 42, .10);
    }
    @media (prefers-color-scheme: dark) {
      :root {
        color-scheme: dark;
        --ink: #edf5f0;
        --muted: #abb8b1;
        --paper: #0f1713;
        --card: #18221d;
        --soft: #243029;
        --line: #34453b;
        --forest: #87cbaa;
        --forest-2: #68bc94;
        --mint: #263f33;
        --cyan: #6ec2cf;
        --amber: #e0b361;
        --orange: #e58a63;
        --red: #e1838c;
        --shadow: 0 22px 60px rgba(0, 0, 0, .28);
      }
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      background:
        radial-gradient(circle at 7% 0%, color-mix(in srgb, var(--forest-2) 13%, transparent), transparent 30rem),
        var(--paper);
      color: var(--ink);
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      line-height: 1.5;
    }
    button, input, select { font: inherit; }
    button, select, input { color: inherit; }
    button:focus-visible, input:focus-visible, select:focus-visible, canvas:focus-visible, a:focus-visible {
      outline: 3px solid color-mix(in srgb, var(--forest-2) 45%, transparent);
      outline-offset: 3px;
    }
    a { color: inherit; }
    .hidden, .hidden-lang { display: none !important; }
    .shell { width: min(1500px, calc(100% - 32px)); margin-inline: auto; }
    header { padding: 22px 0 18px; }
    nav { display: flex; justify-content: space-between; align-items: center; gap: 18px; }
    .brand { display: flex; align-items: center; gap: 11px; font-weight: 780; letter-spacing: -.02em; }
    .brand-mark { width: 36px; height: 36px; display: grid; place-items: center; border-radius: 11px; color: #fff; background: var(--forest); box-shadow: var(--shadow); }
    .nav-actions { display: flex; gap: 8px; align-items: center; }
    .nav-button { display: inline-flex; align-items: center; min-height: 36px; padding: 7px 12px; border: 1px solid var(--line); border-radius: 999px; background: var(--card); text-decoration: none; cursor: pointer; }
    .hero { padding: 34px 0 28px; display: grid; grid-template-columns: minmax(0, 1.35fr) minmax(290px, .65fr); gap: 26px; align-items: end; }
    .eyebrow { margin: 0 0 9px; color: var(--forest); font-size: .76rem; font-weight: 760; letter-spacing: .13em; text-transform: uppercase; }
    h1 { margin: 0; font-size: clamp(2.25rem, 4.4vw, 4.35rem); line-height: .96; letter-spacing: -.06em; }
    .hero-copy { margin: 17px 0 0; max-width: 800px; color: var(--muted); font-size: clamp(.96rem, 1.3vw, 1.08rem); }
    .demo-callout { padding: 17px; border: 1px solid color-mix(in srgb, var(--forest-2) 40%, var(--line)); border-radius: 18px; background: color-mix(in srgb, var(--forest-2) 8%, var(--card)); }
    .demo-callout p { margin: 0 0 12px; font-size: .8rem; color: var(--muted); }
    .primary-button, .secondary-button, .tool-button {
      border: 0; border-radius: 11px; cursor: pointer; font-weight: 720; transition: transform 140ms, opacity 140ms, background 140ms;
    }
    .primary-button { padding: 11px 15px; background: var(--forest); color: #fff; }
    .secondary-button { padding: 9px 12px; border: 1px solid var(--line); background: var(--card); color: var(--ink); }
    .tool-button { padding: 8px 11px; border: 1px solid var(--line); background: var(--soft); color: var(--ink); font-size: .76rem; }
    .primary-button:not(:disabled):hover, .secondary-button:not(:disabled):hover, .tool-button:not(:disabled):hover { transform: translateY(-1px); }
    button:disabled { cursor: not-allowed; opacity: .42; }
    main { padding-bottom: 60px; }
    .workspace { display: grid; grid-template-columns: minmax(520px, 1.08fr) minmax(380px, .92fr); gap: 18px; align-items: start; }
    .card { background: var(--card); border: 1px solid var(--line); border-radius: 20px; box-shadow: var(--shadow); }
    .workbench { overflow: hidden; }
    .section { padding: 18px; border-bottom: 1px solid var(--line); }
    .section:last-child { border-bottom: 0; }
    .section-head { display: flex; align-items: flex-start; justify-content: space-between; gap: 14px; margin-bottom: 13px; }
    h2, h3 { margin: 0; letter-spacing: -.025em; }
    h2 { font-size: 1.06rem; }
    h3 { font-size: .9rem; }
    .step { flex: none; padding: 3px 8px; border-radius: 999px; background: var(--mint); color: var(--forest); font-size: .68rem; font-weight: 760; }
    .subcopy { margin: 4px 0 0; color: var(--muted); font-size: .74rem; }
    .upload-row { display: grid; grid-template-columns: 1fr auto; gap: 10px; align-items: center; }
    .file-label { position: relative; min-width: 0; padding: 12px 14px; border: 1px dashed color-mix(in srgb, var(--forest) 55%, var(--line)); border-radius: 12px; background: var(--soft); cursor: pointer; }
    .file-label input { position: absolute; inset: 0; opacity: 0; cursor: pointer; }
    .file-title { display: block; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-weight: 700; font-size: .82rem; }
    .file-meta { display: block; margin-top: 2px; color: var(--muted); font-size: .7rem; }
    .canvas-shell { position: relative; min-height: 320px; display: grid; place-items: center; overflow: hidden; border-radius: 15px; background: #101713; }
    #editor-canvas { display: block; width: 100%; height: auto; max-height: 720px; object-fit: contain; touch-action: none; cursor: crosshair; }
    .canvas-empty { position: absolute; inset: 0; display: grid; place-items: center; padding: 34px; color: #b6c4bc; text-align: center; pointer-events: none; }
    .toolbar { display: flex; flex-wrap: wrap; gap: 8px; align-items: center; margin-top: 11px; }
    .tool-button.active { border-color: var(--forest-2); background: var(--forest); color: #fff; }
    .brush-control { display: flex; align-items: center; gap: 8px; margin-left: auto; color: var(--muted); font-size: .72rem; }
    .brush-control input { width: 112px; accent-color: var(--forest-2); }
    .mode-grid { display: grid; grid-template-columns: minmax(150px, .7fr) minmax(0, 1.3fr); gap: 13px; }
    .field { display: grid; gap: 5px; }
    .field label { color: var(--muted); font-size: .7rem; font-weight: 680; }
    .field input, .field select { width: 100%; min-height: 40px; padding: 8px 10px; border: 1px solid var(--line); border-radius: 10px; background: var(--soft); }
    .physical-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 9px; }
    .advanced-grid { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 9px; margin-top: 9px; }
    .point-panel { margin-top: 11px; padding: 11px; border-radius: 12px; background: var(--soft); }
    .point-head { display: flex; justify-content: space-between; gap: 12px; align-items: center; }
    .point-list { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 7px; margin-top: 8px; }
    .point-chip { padding: 7px 8px; border: 1px solid var(--line); border-radius: 9px; font-size: .68rem; color: var(--muted); }
    .point-chip strong { display: block; color: var(--ink); }
    .run-row { display: flex; justify-content: space-between; gap: 14px; align-items: center; }
    .privacy { margin: 0; max-width: 570px; color: var(--muted); font-size: .72rem; }
    .status { min-height: 22px; margin: 10px 0 0; color: var(--muted); font-size: .76rem; }
    .status.error { color: var(--red); }
    .results { display: grid; gap: 18px; position: sticky; top: 14px; }
    .placeholder { min-height: 530px; display: grid; place-items: center; padding: 36px; text-align: center; color: var(--muted); }
    .placeholder-mark { width: 104px; height: 104px; margin: 0 auto 17px; display: grid; place-items: center; border-radius: 31px; background: var(--soft); color: var(--forest); font-size: 2.15rem; font-weight: 800; transform: rotate(-4deg); }
    .result-card { overflow: hidden; }
    .artifact-frame { min-height: 330px; display: grid; place-items: center; background: #0e1511; }
    .artifact-frame img { display: block; width: 100%; max-height: 590px; object-fit: contain; }
    .artifact-tabs { display: flex; flex-wrap: wrap; gap: 7px; padding: 12px 14px; border-top: 1px solid var(--line); }
    .artifact-button { padding: 6px 9px; border: 1px solid var(--line); border-radius: 999px; background: var(--card); color: var(--muted); cursor: pointer; font-size: .68rem; }
    .artifact-button.active { border-color: var(--forest-2); background: var(--mint); color: var(--forest); font-weight: 700; }
    .result-summary { padding: 16px; }
    .result-heading { display: flex; align-items: flex-start; justify-content: space-between; gap: 12px; }
    .mode-badge { padding: 4px 8px; border: 1px solid currentColor; border-radius: 999px; color: var(--forest-2); font-size: .68rem; font-weight: 730; }
    .metric-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 9px; margin-top: 14px; }
    .metric { min-width: 0; padding: 11px; border: 1px solid var(--line); border-radius: 12px; background: var(--soft); }
    .metric-label { display: block; overflow: hidden; color: var(--muted); font-size: .65rem; white-space: nowrap; text-overflow: ellipsis; }
    .metric-value { display: block; margin-top: 3px; font-size: 1.28rem; font-weight: 790; letter-spacing: -.04em; }
    .decision { margin: 13px 0 0; padding: 11px 12px; border-left: 4px solid var(--amber); border-radius: 0 10px 10px 0; background: color-mix(in srgb, var(--amber) 8%, var(--card)); color: var(--muted); font-size: .72rem; }
    .evidence { margin-top: 12px; display: grid; gap: 7px; }
    .evidence-row { display: flex; justify-content: space-between; gap: 12px; padding-top: 7px; border-top: 1px solid var(--line); font-size: .72rem; }
    .evidence-row span { color: var(--muted); }
    details { margin-top: 13px; border-top: 1px solid var(--line); padding-top: 10px; }
    summary { cursor: pointer; color: var(--muted); font-size: .72rem; }
    pre { max-height: 360px; overflow: auto; padding: 11px; border-radius: 10px; background: #111915; color: #dceae2; font: 11px/1.5 ui-monospace, SFMono-Regular, Menlo, monospace; white-space: pre-wrap; word-break: break-word; }
    footer { padding: 4px 0 34px; color: var(--muted); font-size: .7rem; }
    @media (max-width: 1050px) {
      .workspace { grid-template-columns: 1fr; }
      .results { position: static; }
    }
    @media (max-width: 720px) {
      .shell { width: min(100% - 20px, 1500px); }
      .hero { grid-template-columns: 1fr; padding-top: 24px; }
      .nav-button.back span { display: none; }
      .mode-grid { grid-template-columns: 1fr; }
      .physical-grid { grid-template-columns: 1fr 1fr; }
      .advanced-grid { grid-template-columns: 1fr 1fr; }
      .point-list, .metric-grid { grid-template-columns: 1fr 1fr; }
      .brush-control { width: 100%; margin-left: 0; }
      .run-row { align-items: stretch; flex-direction: column; }
      .primary-button { width: 100%; }
    }
    @media (prefers-reduced-motion: reduce) {
      *, *::before, *::after { transition: none !important; scroll-behavior: auto !important; }
    }
  </style>
</head>
<body>
  <header class="shell">
    <nav aria-label="Primary">
      <div class="brand"><span class="brand-mark" aria-hidden="true">UV</span><span>UrbanVision-Risk</span></div>
      <div class="nav-actions">
        <a class="nav-button back" href="/"><span aria-hidden="true">←&nbsp;</span><span data-zh>返回检测台</span><span data-en class="hidden-lang">Detection console</span></a>
        <button id="language-button" class="nav-button" type="button">English</button>
      </div>
    </nav>
    <section class="hero">
      <div>
        <p class="eyebrow">v3.1 · Calibrated surface metrology</p>
        <h1><span data-zh>从检测框，走到<br>可验证的真实量测。</span><span data-en class="hidden-lang">From boxes to<br>verifiable measurement.</span></h1>
        <p class="hero-copy"><span data-zh>在原图上绘制裂缝掩膜，选择像素、手动四点或 ArUco 自动标定。系统将在本机计算骨架图、长度、宽度分布、分叉、方向和敏感性区间。</span><span data-en class="hidden-lang">Draw a crack mask, then choose pixel-only, manual four-point, or automatic ArUco calibration. Skeleton graphs, length, width distributions, branching, orientation, and sensitivity intervals are computed locally.</span></p>
      </div>
      <aside class="demo-callout">
        <p><span data-zh>第一次使用？先运行内置标定样本，不需要上传或画图。</span><span data-en class="hidden-lang">First time here? Run the calibrated built-in sample—no upload or drawing required.</span></p>
        <button id="demo-button" class="primary-button" type="button"><span data-zh>运行完整标定 Demo</span><span data-en class="hidden-lang">Run calibrated demo</span></button>
      </aside>
    </section>
  </header>

  <main class="shell">
    <div class="workspace">
      <section class="card workbench">
        <div class="section">
          <div class="section-head">
            <div><h2><span data-zh>选择道路原图</span><span data-en class="hidden-lang">Choose source image</span></h2><p class="subcopy">JPEG · PNG · WebP · ≤ 15 MiB · ≤ 20 MP</p></div>
            <span class="step">01 · SOURCE</span>
          </div>
          <div class="upload-row">
            <label class="file-label">
              <input id="source-input" type="file" accept="image/jpeg,image/png,image/webp">
              <span id="file-title" class="file-title"><span data-zh>点击选择道路图片</span><span data-en class="hidden-lang">Click to choose a road image</span></span>
              <span id="file-meta" class="file-meta"><span data-zh>图片不会发送到互联网</span><span data-en class="hidden-lang">The image never leaves this machine</span></span>
            </label>
            <button id="replace-button" class="secondary-button" type="button" disabled><span data-zh>重新选择</span><span data-en class="hidden-lang">Replace</span></button>
          </div>
        </div>

        <div class="section">
          <div class="section-head">
            <div><h2><span data-zh>绘制裂缝掩膜</span><span data-en class="hidden-lang">Draw crack mask</span></h2><p class="subcopy"><span data-zh>绿色区域是将被量测的裂缝；检测框不会被冒充为掩膜。</span><span data-en class="hidden-lang">Green is the surface to measure; detector boxes are never treated as masks.</span></p></div>
            <span class="step">02 · MASK</span>
          </div>
          <div class="canvas-shell">
            <canvas id="editor-canvas" tabindex="0" aria-label="Road image mask editor"></canvas>
            <div id="canvas-empty" class="canvas-empty"><span><strong><span data-zh>先选择一张原图</span><span data-en class="hidden-lang">Choose an image first</span></strong><br><span data-zh>然后使用画笔覆盖裂缝表面</span><span data-en class="hidden-lang">Then paint over the crack surface</span></span></div>
          </div>
          <div class="toolbar" aria-label="Mask tools">
            <button id="brush-tool" class="tool-button active" type="button" disabled><span data-zh>画笔</span><span data-en class="hidden-lang">Brush</span></button>
            <button id="eraser-tool" class="tool-button" type="button" disabled><span data-zh>橡皮</span><span data-en class="hidden-lang">Eraser</span></button>
            <button id="point-tool" class="tool-button" type="button" disabled><span data-zh>标定点</span><span data-en class="hidden-lang">Calibration points</span></button>
            <button id="undo-button" class="tool-button" type="button" disabled><span data-zh>撤销</span><span data-en class="hidden-lang">Undo</span></button>
            <button id="clear-button" class="tool-button" type="button" disabled><span data-zh>清空</span><span data-en class="hidden-lang">Clear</span></button>
            <label class="brush-control"><span><span data-zh>笔宽</span><span data-en class="hidden-lang">Brush</span> <strong id="brush-value">18</strong> px</span><input id="brush-size" type="range" min="2" max="100" value="18" disabled></label>
          </div>
        </div>

        <div class="section">
          <div class="section-head">
            <div><h2><span data-zh>选择标定方式</span><span data-en class="hidden-lang">Choose calibration</span></h2><p class="subcopy"><span data-zh>没有可靠参考尺寸时必须选择“仅像素”。</span><span data-en class="hidden-lang">Use pixel-only when no trustworthy physical reference exists.</span></p></div>
            <span class="step">03 · CALIBRATE</span>
          </div>
          <div class="mode-grid">
            <div class="field">
              <label for="calibration-mode"><span data-zh>标定模式</span><span data-en class="hidden-lang">Calibration mode</span></label>
              <select id="calibration-mode">
                <option value="pixel">Pixel only / 仅像素</option>
                <option value="manual">Manual 4 points / 手动四点</option>
                <option value="aruco">Auto ArUco / 自动标记</option>
              </select>
            </div>
            <div id="physical-fields" class="physical-grid hidden">
              <div class="field"><label for="physical-width"><span data-zh>真实宽度</span><span data-en class="hidden-lang">Physical width</span></label><input id="physical-width" type="number" min="0.0001" step="any" value="1.2"></div>
              <div class="field"><label for="physical-height"><span data-zh>真实高度</span><span data-en class="hidden-lang">Physical height</span></label><input id="physical-height" type="number" min="0.0001" step="any" value="0.8"></div>
              <div class="field"><label for="physical-unit"><span data-zh>单位</span><span data-en class="hidden-lang">Unit</span></label><select id="physical-unit"><option value="m">m</option><option value="cm">cm</option><option value="mm">mm</option></select></div>
            </div>
          </div>
          <div id="advanced-fields" class="advanced-grid hidden">
            <div class="field"><label for="pixels-per-unit"><span data-zh>每单位像素</span><span data-en class="hidden-lang">Pixels per unit</span></label><input id="pixels-per-unit" type="number" min="0.1" step="any" value="400"></div>
            <div class="field"><label for="point-sigma"><span data-zh>点位 σ（像素）</span><span data-en class="hidden-lang">Point σ (px)</span></label><input id="point-sigma" type="number" min="0" max="20" step="0.1" value="1.5"></div>
            <div class="field"><label for="uncertainty-samples"><span data-zh>扰动样本数</span><span data-en class="hidden-lang">MC samples</span></label><input id="uncertainty-samples" type="number" min="0" max="512" step="1" value="64"></div>
            <div class="field"><label for="boundary-radius"><span data-zh>边界扰动（像素）</span><span data-en class="hidden-lang">Boundary radius</span></label><input id="boundary-radius" type="number" min="0" max="5" step="1" value="1"></div>
          </div>
          <div id="point-panel" class="point-panel hidden">
            <div class="point-head"><div><strong><span data-zh>依次点击 TL → TR → BR → BL</span><span data-en class="hidden-lang">Click TL → TR → BR → BL in order</span></strong><p class="subcopy"><span data-zh>四点必须围成与道路同平面的已测矩形。</span><span data-en class="hidden-lang">The four points must enclose a measured coplanar rectangle.</span></p></div><button id="reset-points" class="tool-button" type="button"><span data-zh>重置四点</span><span data-en class="hidden-lang">Reset points</span></button></div>
            <div id="point-list" class="point-list"></div>
          </div>
          <div id="aruco-note" class="point-panel hidden"><strong>IDs 17 / 23 / 42 / 56</strong><p class="subcopy"><span data-zh>程序将自动寻找 TL/TR/BR/BL 标记中心。这里填写的是现场用卷尺测得的中心间宽高。</span><span data-en class="hidden-lang">Marker centers are detected automatically. Enter the tape-measured center-to-center width and height above.</span></p></div>
        </div>

        <div class="section">
          <div class="run-row">
            <p class="privacy"><span data-zh>原图与掩膜只提交到本机回环地址；结果保存在本地且不会覆盖。真实尺寸只适用于标定平面，不是道路安全认证。</span><span data-en class="hidden-lang">Source and mask go only to loopback. Results are local and immutable. Physical dimensions apply only to the calibrated plane and are not a road-safety certification.</span></p>
            <button id="measure-button" class="primary-button" type="button" disabled><span data-zh>运行本地精密量测</span><span data-en class="hidden-lang">Run local metrology</span></button>
          </div>
          <p id="status" class="status" aria-live="polite"></p>
        </div>
      </section>

      <aside class="results" aria-live="polite">
        <section id="placeholder" class="card placeholder">
          <div><div class="placeholder-mark" aria-hidden="true">μ</div><strong><span data-zh>量测结果将在这里出现</span><span data-en class="hidden-lang">Measurements appear here</span></strong><p><span data-zh>先运行内置 Demo，或上传图片并绘制白色裂缝掩膜。</span><span data-en class="hidden-lang">Run the built-in demo, or upload an image and draw a white crack mask.</span></p></div>
        </section>
        <section id="result" class="card result-card hidden">
          <div class="artifact-frame"><img id="artifact-image" alt="Metrology artifact"></div>
          <div id="artifact-tabs" class="artifact-tabs"></div>
          <div class="result-summary">
            <div class="result-heading"><div><h2><span data-zh>裂缝几何与拓扑</span><span data-en class="hidden-lang">Crack geometry and topology</span></h2><p id="run-id" class="subcopy">—</p></div><span id="mode-badge" class="mode-badge">—</span></div>
            <div class="metric-grid">
              <div class="metric"><span class="metric-label"><span data-zh>网络长度</span><span data-en class="hidden-lang">Network length</span></span><strong id="metric-length" class="metric-value">—</strong></div>
              <div class="metric"><span class="metric-label"><span data-zh>平均宽度</span><span data-en class="hidden-lang">Mean width</span></span><strong id="metric-width" class="metric-value">—</strong></div>
              <div class="metric"><span class="metric-label">P95 width / P95 宽度</span><strong id="metric-p95" class="metric-value">—</strong></div>
              <div class="metric"><span class="metric-label"><span data-zh>连通分量</span><span data-en class="hidden-lang">Components</span></span><strong id="metric-components" class="metric-value">—</strong></div>
              <div class="metric"><span class="metric-label"><span data-zh>端点 / 分叉</span><span data-en class="hidden-lang">Endpoints / junctions</span></span><strong id="metric-nodes" class="metric-value">—</strong></div>
              <div class="metric"><span class="metric-label"><span data-zh>主方向</span><span data-en class="hidden-lang">Orientation</span></span><strong id="metric-orientation" class="metric-value">—</strong></div>
            </div>
            <p id="decision" class="decision">—</p>
            <div id="evidence" class="evidence"></div>
            <details><summary><span data-zh>查看完整 measurement.json</span><span data-en class="hidden-lang">View complete measurement.json</span></summary><pre id="json-output"></pre></details>
          </div>
        </section>
      </aside>
    </div>
  </main>
  <footer class="shell">UrbanVision-Risk v3.1 · Precision Lab · Fully local / 完全本地</footer>

  <script>
    (() => {
      const byId = (id) => document.getElementById(id);
      const editor = byId("editor-canvas");
      const editorContext = editor.getContext("2d");
      const maskCanvas = document.createElement("canvas");
      const maskContext = maskCanvas.getContext("2d");
      const tintCanvas = document.createElement("canvas");
      const tintContext = tintCanvas.getContext("2d");
      const labels = ["TL", "TR", "BR", "BL"];
      let language = "zh";
      let sourceFile = null;
      let sourceImage = null;
      let sourceUrl = null;
      let tool = "brush";
      let drawing = false;
      let activeStroke = null;
      let strokes = [];
      let calibrationPoints = [];
      let latestResult = null;

      const text = {
        zh: {
          choose: "点击选择道路图片",
          private: "图片不会发送到互联网",
          ready: "原图已就绪。请使用画笔覆盖裂缝表面。",
          drawingRequired: "请先选择原图并绘制裂缝掩膜。",
          pointsRequired: "手动标定需要依次点击 TL、TR、BR、BL 四个点。",
          measuring: "正在本机提取骨架、构建图结构并计算不确定性…",
          demoRunning: "正在生成完整标定 Demo…",
          complete: "量测完成，结果已保存在本机。",
          demoComplete: "标定 Demo 完成；这是算法演示，不是现场精度证明。",
          failed: "量测失败，请检查终端日志。",
          pixel: "仅像素",
          physical: "真实平面",
          overlay: "叠加图",
          rectified: "矫正图",
          width: "宽度热图",
          rectifiedWidth: "矫正宽度",
          skeleton: "骨架",
          interval: "长度敏感性 p05–p95",
          tortuosity: "主路径曲折度",
          fractal: "盒计数维数",
          aruco: "ArUco 最小标记周长",
          quad: "标定区域画面占比"
        },
        en: {
          choose: "Click to choose a road image",
          private: "The image never leaves this machine",
          ready: "Source ready. Paint over the crack surface.",
          drawingRequired: "Choose a source image and draw a crack mask first.",
          pointsRequired: "Manual calibration needs TL, TR, BR, and BL clicks in order.",
          measuring: "Extracting the skeleton, graph, geometry, and uncertainty locally…",
          demoRunning: "Generating the full calibrated demo…",
          complete: "Metrology complete and saved locally.",
          demoComplete: "Calibrated demo complete; this proves software behavior, not field accuracy.",
          failed: "Metrology failed; check the terminal log.",
          pixel: "Pixel only",
          physical: "Physical plane",
          overlay: "Overlay",
          rectified: "Rectified",
          width: "Width heatmap",
          rectifiedWidth: "Rectified width",
          skeleton: "Skeleton",
          interval: "Length sensitivity p05–p95",
          tortuosity: "Main-path tortuosity",
          fractal: "Box-counting dimension",
          aruco: "Minimum ArUco perimeter",
          quad: "Calibration image ratio"
        }
      };
      const t = (key) => text[language][key] || key;

      function setStatus(message, error = false) {
        byId("status").textContent = message;
        byId("status").classList.toggle("error", error);
      }

      function applyLanguage() {
        document.documentElement.lang = language === "zh" ? "zh-CN" : "en";
        document.querySelectorAll("[data-zh]").forEach((item) => item.classList.toggle("hidden-lang", language !== "zh"));
        document.querySelectorAll("[data-en]").forEach((item) => item.classList.toggle("hidden-lang", language !== "en"));
        byId("language-button").textContent = language === "zh" ? "English" : "中文";
        if (!sourceFile) {
          byId("file-title").textContent = t("choose");
          byId("file-meta").textContent = t("private");
        }
        if (latestResult) renderResult(latestResult);
      }

      function canvasPosition(event) {
        const rectangle = editor.getBoundingClientRect();
        return {
          x: Math.max(0, Math.min(editor.width - 1, (event.clientX - rectangle.left) * editor.width / rectangle.width)),
          y: Math.max(0, Math.min(editor.height - 1, (event.clientY - rectangle.top) * editor.height / rectangle.height))
        };
      }

      function initializeMask() {
        resetMask();
        calibrationPoints = [];
        updatePointList();
      }

      function resetMask() {
        maskContext.globalCompositeOperation = "source-over";
        maskContext.fillStyle = "#000";
        maskContext.fillRect(0, 0, maskCanvas.width, maskCanvas.height);
        strokes = [];
        activeStroke = null;
      }

      function drawStroke(context, stroke) {
        if (!stroke.points.length) return;
        context.save();
        context.globalCompositeOperation = "source-over";
        context.strokeStyle = stroke.tool === "eraser" ? "#000" : "#fff";
        context.fillStyle = context.strokeStyle;
        context.lineWidth = stroke.size;
        context.lineCap = "round";
        context.lineJoin = "round";
        context.beginPath();
        context.moveTo(stroke.points[0].x, stroke.points[0].y);
        stroke.points.slice(1).forEach((point) => context.lineTo(point.x, point.y));
        if (stroke.points.length === 1) {
          context.arc(stroke.points[0].x, stroke.points[0].y, stroke.size / 2, 0, Math.PI * 2);
          context.fill();
        } else {
          context.stroke();
        }
        context.restore();
      }

      function rebuildMask() {
        maskContext.fillStyle = "#000";
        maskContext.fillRect(0, 0, maskCanvas.width, maskCanvas.height);
        strokes.forEach((stroke) => drawStroke(maskContext, stroke));
      }

      function renderEditor() {
        if (!sourceImage) return;
        editorContext.clearRect(0, 0, editor.width, editor.height);
        editorContext.drawImage(sourceImage, 0, 0, editor.width, editor.height);
        tintContext.clearRect(0, 0, tintCanvas.width, tintCanvas.height);
        tintContext.globalCompositeOperation = "source-over";
        tintContext.fillStyle = "#2ee6a0";
        tintContext.fillRect(0, 0, tintCanvas.width, tintCanvas.height);
        tintContext.globalCompositeOperation = "destination-in";
        tintContext.drawImage(maskCanvas, 0, 0);
        tintContext.globalCompositeOperation = "source-over";
        editorContext.save();
        editorContext.globalAlpha = .55;
        editorContext.drawImage(tintCanvas, 0, 0);
        editorContext.restore();

        if (calibrationPoints.length) {
          const scale = Math.max(2, Math.min(editor.width, editor.height) / 300);
          editorContext.save();
          editorContext.lineWidth = scale;
          editorContext.strokeStyle = "#ffd34d";
          editorContext.fillStyle = "#ffd34d";
          editorContext.font = `${Math.max(14, scale * 5)}px -apple-system, sans-serif`;
          editorContext.beginPath();
          calibrationPoints.forEach((point, index) => {
            if (index === 0) editorContext.moveTo(point.x, point.y);
            else editorContext.lineTo(point.x, point.y);
          });
          if (calibrationPoints.length === 4) editorContext.closePath();
          editorContext.stroke();
          calibrationPoints.forEach((point, index) => {
            editorContext.beginPath();
            editorContext.arc(point.x, point.y, scale * 2.2, 0, Math.PI * 2);
            editorContext.fill();
            editorContext.fillText(labels[index], point.x + scale * 3, point.y - scale * 3);
          });
          editorContext.restore();
        }
      }

      function setTool(nextTool) {
        tool = nextTool;
        ["brush", "eraser", "point"].forEach((name) => byId(`${name}-tool`).classList.toggle("active", name === tool));
        editor.style.cursor = tool === "point" ? "cell" : "crosshair";
      }

      function updateControls() {
        const ready = Boolean(sourceImage);
        ["brush-tool", "eraser-tool", "clear-button", "brush-size"].forEach((id) => { byId(id).disabled = !ready; });
        byId("point-tool").disabled = !ready || byId("calibration-mode").value !== "manual";
        byId("undo-button").disabled = !ready || strokes.length === 0;
        byId("replace-button").disabled = !ready;
        byId("measure-button").disabled = !ready || strokes.length === 0;
      }

      function updatePointList() {
        const list = byId("point-list");
        list.replaceChildren();
        labels.forEach((label, index) => {
          const chip = document.createElement("div");
          chip.className = "point-chip";
          const title = document.createElement("strong");
          title.textContent = label;
          const value = document.createElement("span");
          const point = calibrationPoints[index];
          value.textContent = point ? `${Math.round(point.x)}, ${Math.round(point.y)}` : "—";
          chip.append(title, value);
          list.appendChild(chip);
        });
      }

      function updateCalibrationUI() {
        const mode = byId("calibration-mode").value;
        const physical = mode !== "pixel";
        byId("physical-fields").classList.toggle("hidden", !physical);
        byId("advanced-fields").classList.toggle("hidden", !physical);
        byId("point-panel").classList.toggle("hidden", mode !== "manual");
        byId("aruco-note").classList.toggle("hidden", mode !== "aruco");
        if (mode === "manual" && sourceImage) setTool("point");
        else if (tool === "point") setTool("brush");
        updateControls();
      }

      async function loadSource(file) {
        if (!file) return;
        if (!["image/jpeg", "image/png", "image/webp"].includes(file.type) || file.size > 15 * 1024 * 1024) {
          setStatus(language === "zh" ? "请选择不超过 15 MiB 的 JPEG、PNG 或 WebP。" : "Choose a JPEG, PNG, or WebP no larger than 15 MiB.", true);
          return;
        }
        if (sourceUrl) URL.revokeObjectURL(sourceUrl);
        sourceUrl = URL.createObjectURL(file);
        const image = new Image();
        image.src = sourceUrl;
        try {
          await image.decode();
        } catch {
          setStatus(language === "zh" ? "浏览器无法解码这张图片。" : "The browser cannot decode this image.", true);
          return;
        }
        if (image.naturalWidth * image.naturalHeight > 20_000_000) {
          setStatus(language === "zh" ? "量测工作台限制为 2000 万像素。" : "The metrology workbench is limited to 20 megapixels.", true);
          return;
        }
        sourceFile = file;
        sourceImage = image;
        editor.width = maskCanvas.width = tintCanvas.width = image.naturalWidth;
        editor.height = maskCanvas.height = tintCanvas.height = image.naturalHeight;
        initializeMask();
        renderEditor();
        byId("canvas-empty").classList.add("hidden");
        byId("file-title").textContent = file.name;
        byId("file-meta").textContent = `${image.naturalWidth} × ${image.naturalHeight} px · ${(file.size / 1024 / 1024).toFixed(2)} MiB`;
        setTool("brush");
        updateControls();
        setStatus(t("ready"));
      }

      function pointerDown(event) {
        if (!sourceImage) return;
        event.preventDefault();
        const point = canvasPosition(event);
        if (tool === "point") {
          if (calibrationPoints.length < 4) {
            calibrationPoints.push(point);
            updatePointList();
            renderEditor();
          }
          return;
        }
        drawing = true;
        editor.setPointerCapture(event.pointerId);
        activeStroke = { tool, size: Number(byId("brush-size").value), points: [point] };
        strokes.push(activeStroke);
        drawStroke(maskContext, activeStroke);
        renderEditor();
        updateControls();
      }

      function pointerMove(event) {
        if (!drawing || !activeStroke) return;
        event.preventDefault();
        const point = canvasPosition(event);
        const previous = activeStroke.points[activeStroke.points.length - 1];
        if (Math.hypot(point.x - previous.x, point.y - previous.y) < 1) return;
        activeStroke.points.push(point);
        drawStroke(maskContext, { ...activeStroke, points: [previous, point] });
        renderEditor();
      }

      function pointerUp(event) {
        if (!drawing) return;
        drawing = false;
        activeStroke = null;
        try { editor.releasePointerCapture(event.pointerId); } catch {}
        updateControls();
      }

      function maskBlob() {
        return new Promise((resolve, reject) => maskCanvas.toBlob((blob) => blob ? resolve(blob) : reject(new Error("mask export failed")), "image/png"));
      }

      function formNumber(id) {
        return String(Number(byId(id).value));
      }

      async function runMeasurement() {
        if (!sourceFile || strokes.length === 0) {
          setStatus(t("drawingRequired"), true);
          return;
        }
        const mode = byId("calibration-mode").value;
        if (mode === "manual" && calibrationPoints.length !== 4) {
          setStatus(t("pointsRequired"), true);
          return;
        }
        byId("measure-button").disabled = true;
        setStatus(t("measuring"));
        try {
          const mask = await maskBlob();
          const form = new FormData();
          form.append("image", sourceFile, sourceFile.name);
          form.append("mask", mask, "browser-mask.png");
          form.append("calibration_mode", mode);
          form.append("uncertainty_samples", formNumber("uncertainty-samples"));
          form.append("segmentation_radius_pixels", formNumber("boundary-radius"));
          if (mode !== "pixel") {
            form.append("physical_width", formNumber("physical-width"));
            form.append("physical_height", formNumber("physical-height"));
            form.append("unit", byId("physical-unit").value);
            form.append("pixels_per_unit", formNumber("pixels-per-unit"));
            form.append("point_sigma_pixels", formNumber("point-sigma"));
          }
          if (mode === "manual") {
            form.append("manual_points", JSON.stringify(calibrationPoints.map((point) => [point.x, point.y])));
          }
          const response = await fetch("/api/metrology/analyze", { method: "POST", body: form });
          const payload = await response.json();
          if (!response.ok) throw payload.error || payload;
          renderResult(payload);
          setStatus(t("complete"));
          byId("result").scrollIntoView({ behavior: "smooth", block: "start" });
        } catch (error) {
          const message = error && (language === "zh" ? error.message_zh : error.message_en);
          const recovery = error && (language === "zh" ? error.recovery_zh : error.recovery_en);
          setStatus([message, recovery].filter(Boolean).join(" — ") || t("failed"), true);
        } finally {
          updateControls();
        }
      }

      async function runDemo() {
        byId("demo-button").disabled = true;
        setStatus(t("demoRunning"));
        try {
          const response = await fetch("/api/metrology/demo", { method: "POST" });
          const payload = await response.json();
          if (!response.ok) throw payload.error || payload;
          renderResult(payload);
          setStatus(t("demoComplete"));
          byId("result").scrollIntoView({ behavior: "smooth", block: "start" });
        } catch (error) {
          const message = error && (language === "zh" ? error.message_zh : error.message_en);
          setStatus(message || t("failed"), true);
        } finally {
          byId("demo-button").disabled = false;
        }
      }

      function formatValue(value, unit, digits = 3) {
        if (value === null || value === undefined) return "—";
        return `${Number(value).toFixed(digits)} ${unit}`;
      }

      function addEvidence(label, value) {
        if (value === null || value === undefined) return;
        const row = document.createElement("div");
        row.className = "evidence-row";
        const left = document.createElement("span");
        left.textContent = label;
        const right = document.createElement("strong");
        right.textContent = String(value);
        row.append(left, right);
        byId("evidence").appendChild(row);
      }

      function selectArtifact(url, button) {
        byId("artifact-image").src = url;
        document.querySelectorAll(".artifact-button").forEach((item) => item.classList.toggle("active", item === button));
      }

      function renderResult(payload) {
        latestResult = payload;
        const measurement = payload.measurement;
        const physical = measurement.physical_geometry;
        const geometry = physical || measurement.pixel_geometry;
        const unit = geometry.unit === "pixel" ? "px" : geometry.unit;
        const topology = measurement.topology;
        const widths = geometry.width_distribution;
        byId("placeholder").classList.add("hidden");
        byId("result").classList.remove("hidden");
        byId("run-id").textContent = payload.run_id;
        byId("mode-badge").textContent = physical ? t("physical") : t("pixel");
        byId("metric-length").textContent = formatValue(geometry.centerline_network_length, unit);
        byId("metric-width").textContent = formatValue(widths.mean, unit);
        byId("metric-p95").textContent = formatValue(widths.p95, unit);
        byId("metric-components").textContent = String(topology.component_count);
        byId("metric-nodes").textContent = `${topology.endpoint_cluster_count} / ${topology.junction_cluster_count}`;
        const orientation = physical ? physical.rectified_principal_orientation_degrees : topology.principal_orientation_degrees;
        byId("metric-orientation").textContent = orientation === null ? "—" : `${Number(orientation).toFixed(1)}°`;
        byId("decision").textContent = measurement.decision_boundary[language === "zh" ? "message_zh" : "message_en"];
        byId("json-output").textContent = JSON.stringify(measurement, null, 2);

        const tabs = byId("artifact-tabs");
        tabs.replaceChildren();
        const artifactChoices = [
          ["rectified-overlay.jpg", t("rectified")],
          ["overlay.jpg", t("overlay")],
          ["rectified-width-heatmap.png", t("rectifiedWidth")],
          ["width-heatmap.png", t("width")],
          ["skeleton.png", t("skeleton")]
        ].filter(([name]) => payload.artifacts[name]);
        artifactChoices.forEach(([name, label], index) => {
          const button = document.createElement("button");
          button.className = `artifact-button${index === 0 ? " active" : ""}`;
          button.type = "button";
          button.textContent = label;
          button.addEventListener("click", () => selectArtifact(payload.artifacts[name], button));
          tabs.appendChild(button);
        });
        if (artifactChoices.length) byId("artifact-image").src = payload.artifacts[artifactChoices[0][0]];

        byId("evidence").replaceChildren();
        const uncertainty = measurement.uncertainty;
        if (uncertainty) {
          const interval = uncertainty.centerline_network_length.interval;
          addEvidence(t("interval"), `${Number(interval.p05).toFixed(3)}–${Number(interval.p95).toFixed(3)} ${unit}`);
        }
        addEvidence(t("tortuosity"), topology.main_path_tortuosity);
        addEvidence(t("fractal"), topology.box_counting_dimension);
        const calibration = measurement.run && measurement.run.input_evidence && measurement.run.input_evidence.calibration;
        const field = calibration && calibration.field_detection;
        if (field) {
          addEvidence(t("aruco"), `${Number(field.minimum_marker_perimeter_pixels).toFixed(1)} px`);
          addEvidence(t("quad"), `${(Number(field.calibration_quadrilateral_image_ratio) * 100).toFixed(1)}%`);
        }
      }

      editor.addEventListener("pointerdown", pointerDown);
      editor.addEventListener("pointermove", pointerMove);
      editor.addEventListener("pointerup", pointerUp);
      editor.addEventListener("pointercancel", pointerUp);
      byId("source-input").addEventListener("change", (event) => loadSource(event.target.files[0]));
      byId("replace-button").addEventListener("click", () => byId("source-input").click());
      byId("brush-tool").addEventListener("click", () => setTool("brush"));
      byId("eraser-tool").addEventListener("click", () => setTool("eraser"));
      byId("point-tool").addEventListener("click", () => setTool("point"));
      byId("brush-size").addEventListener("input", () => { byId("brush-value").textContent = byId("brush-size").value; });
      byId("undo-button").addEventListener("click", () => {
        strokes.pop();
        rebuildMask();
        renderEditor();
        updateControls();
      });
      byId("clear-button").addEventListener("click", () => {
        resetMask();
        renderEditor();
        updateControls();
      });
      byId("reset-points").addEventListener("click", () => {
        calibrationPoints = [];
        updatePointList();
        renderEditor();
      });
      byId("calibration-mode").addEventListener("change", updateCalibrationUI);
      byId("physical-unit").addEventListener("change", () => {
        const defaults = { m: 400, cm: 4, mm: .4 };
        byId("pixels-per-unit").value = String(defaults[byId("physical-unit").value]);
      });
      byId("measure-button").addEventListener("click", runMeasurement);
      byId("demo-button").addEventListener("click", runDemo);
      byId("language-button").addEventListener("click", () => {
        language = language === "zh" ? "en" : "zh";
        applyLanguage();
      });
      updatePointList();
      updateCalibrationUI();
      applyLanguage();
    })();
  </script>
</body>
</html>
"""
