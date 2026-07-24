# ruff: noqa: E501, RUF001
"""Self-contained calibrated metrology workbench / 自包含标定量测工作台。"""

METROLOGY_HTML = """<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>UrbanVision-Risk · Unified Local Inspection</title>
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
    .tool-button.hotspot.active { border-color: var(--amber); background: var(--amber); color: #fff; }
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
    .pipeline-rail { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 7px; margin-top: 10px; }
    .pipeline-stage { position: relative; padding: 8px 9px 8px 25px; border: 1px solid var(--line); border-radius: 10px; background: var(--card); color: var(--muted); font-size: .66rem; }
    .pipeline-stage::before { content: ""; position: absolute; left: 9px; top: 50%; width: 8px; height: 8px; border-radius: 50%; background: var(--line); transform: translateY(-50%); }
    .pipeline-stage.active { border-color: color-mix(in srgb, var(--forest-2) 55%, var(--line)); color: var(--forest); font-weight: 720; }
    .pipeline-stage.active::before { background: var(--amber); box-shadow: 0 0 0 4px color-mix(in srgb, var(--amber) 15%, transparent); }
    .pipeline-stage.complete { border-color: color-mix(in srgb, var(--forest-2) 35%, var(--line)); background: var(--mint); color: var(--forest); }
    .pipeline-stage.complete::before { background: var(--forest-2); }
    .inspection-loading { display: flex; align-items: center; gap: 9px; padding: 12px; border-radius: 12px; background: var(--soft); color: var(--muted); font-size: .76rem; }
    .spinner { width: 16px; height: 16px; flex: none; border: 2px solid var(--line); border-top-color: var(--forest-2); border-radius: 50%; animation: spin 800ms linear infinite; }
    @keyframes spin { to { transform: rotate(360deg); } }
    .inspection-overview { display: grid; grid-template-columns: minmax(0, 1.35fr) minmax(190px, .65fr); gap: 12px; }
    .inspection-visual { min-height: 250px; display: grid; place-items: center; overflow: hidden; border-radius: 14px; background: #101713; }
    .inspection-visual img { display: block; width: 100%; max-height: 520px; object-fit: contain; }
    .inspection-summary { display: flex; flex-direction: column; justify-content: center; gap: 10px; padding: 14px; border: 1px solid var(--line); border-radius: 14px; background: var(--soft); }
    .inspection-score { font-size: 2.6rem; line-height: 1; font-weight: 800; letter-spacing: -.06em; }
    .inspection-score small { font-size: .72rem; color: var(--muted); letter-spacing: 0; }
    .badges { display: flex; flex-wrap: wrap; gap: 6px; }
    .badge { display: inline-flex; width: fit-content; padding: 4px 8px; border: 1px solid currentColor; border-radius: 999px; color: var(--forest); font-size: .66rem; font-weight: 720; }
    .badge-review_required, .badge-low { color: var(--orange); }
    .badge-high, .badge-critical { color: var(--red); }
    .inspection-recommendation { margin: 0; padding: 10px; border-radius: 10px; background: var(--card); color: var(--muted); font-size: .72rem; }
    .inspection-grid { display: grid; grid-template-columns: repeat(5, minmax(0, 1fr)); gap: 7px; margin-top: 10px; }
    .inspection-class { min-width: 0; padding: 9px; border: 1px solid var(--line); border-radius: 10px; background: var(--soft); }
    .inspection-class-code { display: block; color: var(--forest); font-size: .67rem; font-weight: 760; }
    .inspection-class-line { display: flex; justify-content: space-between; gap: 6px; align-items: end; margin-top: 5px; }
    .inspection-class-name { overflow: hidden; color: var(--muted); font-size: .65rem; text-overflow: ellipsis; white-space: nowrap; }
    .inspection-class-count { font-size: 1.08rem; }
    .inspection-evidence-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 9px; margin-top: 10px; }
    .inspection-evidence { padding: 11px; border: 1px solid var(--line); border-radius: 11px; background: var(--card); }
    .inspection-evidence h3 { margin-bottom: 6px; font-size: .78rem; }
    .inspection-evidence-row { display: flex; justify-content: space-between; gap: 9px; padding: 5px 0; border-bottom: 1px solid var(--line); font-size: .67rem; }
    .inspection-evidence-row:last-child { border-bottom: 0; }
    .inspection-evidence-row span { color: var(--muted); }
    .inspection-flags { display: grid; gap: 5px; margin-top: 8px; }
    .inspection-flag { margin: 0; padding: 7px 8px; border-radius: 8px; background: color-mix(in srgb, var(--amber) 9%, var(--card)); color: var(--muted); font-size: .67rem; }
    .inspection-record { margin: 8px 0 0; color: var(--muted); font: 10px/1.4 ui-monospace, SFMono-Regular, Menlo, monospace; overflow-wrap: anywhere; }
    .narrative-panel { margin-top: 10px; padding: 11px; border: 1px solid var(--line); border-radius: 11px; background: var(--soft); }
    .narrative-head { display: flex; justify-content: space-between; gap: 10px; align-items: center; }
    .narrative-content { margin-top: 8px; color: var(--muted); font-size: .7rem; }
    .narrative-content ul { margin: 6px 0; padding-left: 18px; }
    .detection-table-wrap { max-height: 250px; margin-top: 8px; overflow: auto; border: 1px solid var(--line); border-radius: 9px; }
    .detection-table { width: 100%; border-collapse: collapse; font-size: .67rem; }
    .detection-table th, .detection-table td { padding: 7px 8px; border-bottom: 1px solid var(--line); text-align: left; white-space: nowrap; }
    .detection-table th { position: sticky; top: 0; background: var(--soft); color: var(--muted); }
    .canvas-shell { position: relative; min-height: 320px; display: grid; place-items: center; overflow: hidden; border-radius: 15px; background: #101713; }
    #editor-canvas { display: block; width: 100%; height: auto; max-height: 720px; object-fit: contain; touch-action: none; cursor: crosshair; }
    .canvas-empty { position: absolute; inset: 0; display: grid; place-items: center; padding: 34px; color: #b6c4bc; text-align: center; pointer-events: none; }
    .toolbar { display: flex; flex-wrap: wrap; gap: 8px; align-items: center; margin-top: 11px; }
    .tool-button.active { border-color: var(--forest-2); background: var(--forest); color: #fff; }
    .brush-control { display: flex; align-items: center; gap: 8px; margin-left: auto; color: var(--muted); font-size: .72rem; }
    .brush-control.proposal-control { margin-left: 0; }
    .brush-control input { width: 112px; accent-color: var(--forest-2); }
    .hotspot-review { margin-top: 11px; padding: 12px; border: 1px solid color-mix(in srgb, var(--amber) 45%, var(--line)); border-radius: 13px; background: color-mix(in srgb, var(--amber) 7%, var(--card)); }
    .hotspot-review-head { display: flex; justify-content: space-between; align-items: center; gap: 12px; }
    .hotspot-review-title { font-size: .76rem; font-weight: 760; }
    .hotspot-review-progress { color: var(--muted); font-size: .68rem; text-align: right; }
    .hotspot-review-body { display: grid; grid-template-columns: minmax(0, .78fr) minmax(260px, 1.22fr); gap: 12px; margin-top: 9px; align-items: stretch; }
    .hotspot-review-actions { display: flex; flex-wrap: wrap; gap: 7px; margin-top: 9px; }
    .hotspot-review-actions .tool-button.reviewed { border-color: var(--forest-2); background: var(--mint); color: var(--forest); }
    .hotspot-review-detail { margin: 8px 0 0; color: var(--muted); font-size: .69rem; }
    .hotspot-review-track { height: 5px; margin-top: 9px; overflow: hidden; border-radius: 999px; background: var(--line); }
    .hotspot-review-bar { display: block; width: 0; height: 100%; border-radius: inherit; background: var(--amber); transition: width 180ms ease; }
    .hotspot-loupe-shell { position: relative; min-height: 170px; display: grid; place-items: center; overflow: hidden; border: 1px solid color-mix(in srgb, var(--amber) 45%, var(--line)); border-radius: 11px; background: #101713; }
    #hotspot-loupe { display: block; width: 100%; height: auto; aspect-ratio: 16 / 9; touch-action: none; cursor: crosshair; }
    .hotspot-loupe-scale { position: absolute; top: 7px; right: 7px; padding: 3px 7px; border-radius: 999px; background: rgba(0, 0, 0, .76); color: #ffd34d; font-size: .64rem; font-weight: 760; pointer-events: none; }
    .hotspot-loupe-help { margin: 7px 0 0; color: var(--muted); font-size: .66rem; }
    .hotspot-decision { margin-top: 10px; padding-top: 9px; border-top: 1px solid color-mix(in srgb, var(--amber) 30%, var(--line)); }
    .hotspot-decision-title { margin: 0 0 6px; color: var(--ink); font-size: .68rem; font-weight: 760; }
    .hotspot-decision-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 6px; }
    .hotspot-decision-button { min-height: 35px; padding: 6px 8px; border: 1px solid var(--line); border-radius: 9px; background: var(--soft); color: var(--ink); font-size: .64rem; font-weight: 700; cursor: pointer; }
    .hotspot-decision-button.selected { border-color: var(--forest-2); background: var(--forest); color: #fff; }
    .hotspot-decision-button.defer.selected { border-color: #9b6a00; background: #9b6a00; }
    .hotspot-note { display: grid; gap: 4px; margin-top: 7px; color: var(--muted); font-size: .64rem; }
    .hotspot-note input { width: 100%; min-height: 34px; padding: 7px 9px; border: 1px solid var(--line); border-radius: 9px; background: var(--card); color: var(--ink); }
    .hotspot-decision-state { min-height: 18px; margin: 6px 0 0; color: var(--muted); font-size: .64rem; }
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
    .review-state { margin: 12px 0 0; padding: 10px 11px; border: 1px solid var(--line); border-radius: 10px; color: var(--muted); font-size: .71rem; }
    .review-state.draft { border-color: color-mix(in srgb, var(--amber) 45%, var(--line)); background: color-mix(in srgb, var(--amber) 8%, var(--card)); }
    .review-state.reviewed { border-color: color-mix(in srgb, var(--forest-2) 45%, var(--line)); background: var(--mint); color: var(--forest); }
    .evidence { margin-top: 12px; display: grid; gap: 7px; }
    .evidence-row { display: flex; justify-content: space-between; gap: 12px; padding-top: 7px; border-top: 1px solid var(--line); font-size: .72rem; }
    .evidence-row span { color: var(--muted); }
    .practical-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-top: 14px; }
    .utility-panel { padding: 12px; border: 1px solid var(--line); border-radius: 13px; background: color-mix(in srgb, var(--soft) 72%, var(--card)); }
    .utility-panel h3 { font-size: .82rem; }
    .utility-panel .subcopy { min-height: 34px; }
    .utility-fields { display: grid; grid-template-columns: 1fr 1fr; gap: 7px; margin-top: 10px; }
    .utility-fields .field input, .utility-fields .field select { min-height: 35px; padding: 6px 8px; font-size: .74rem; }
    .utility-button { width: 100%; margin-top: 9px; padding: 8px 10px; border: 0; border-radius: 9px; background: var(--forest); color: #fff; cursor: pointer; font-size: .73rem; font-weight: 720; }
    .utility-result { margin-top: 9px; padding: 9px; border-radius: 9px; background: var(--card); font-size: .71rem; }
    .utility-result strong { display: block; margin-bottom: 3px; color: var(--forest); font-size: .86rem; }
    .utility-result.alert strong { color: var(--orange); }
    .download-link { display: inline-block; margin-top: 5px; color: var(--forest); font-weight: 700; }
    .change-map { margin-top: 10px; overflow: hidden; border: 1px solid var(--line); border-radius: 10px; background: #101713; }
    .change-map img { display: block; width: 100%; max-height: 280px; object-fit: contain; image-rendering: auto; }
    .change-legend { display: flex; flex-wrap: wrap; gap: 7px 12px; padding: 8px 9px; background: var(--card); color: var(--muted); font-size: .65rem; }
    .legend-item { display: inline-flex; align-items: center; gap: 5px; }
    .legend-dot { width: 8px; height: 8px; border-radius: 50%; }
    .legend-stable { background: rgb(115, 193, 99); }
    .legend-added { background: rgb(239, 119, 58); }
    .legend-missing { background: rgb(57, 133, 226); }
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
      .inspection-overview, .inspection-evidence-grid { grid-template-columns: 1fr; }
      .inspection-grid { grid-template-columns: 1fr 1fr; }
      .hotspot-review-body { grid-template-columns: 1fr; }
      .pipeline-rail { grid-template-columns: 1fr 1fr; }
      .practical-grid { grid-template-columns: 1fr; }
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
        <span class="nav-button"><span data-zh>本机自动流水线</span><span data-en class="hidden-lang">On-device auto pipeline</span></span>
        <button id="language-button" class="nav-button" type="button">English</button>
      </div>
    </nav>
    <section class="hero">
      <div>
        <p class="eyebrow">v4.7 · Active-learning feedback export</p>
        <h1><span data-zh>上传一次，自动巡检到<br>可验证的真实量测。</span><span data-en class="hidden-lang">One upload, from inspection<br>to verifiable measurement.</span></h1>
        <p class="hero-copy"><span data-zh>每个黄色分歧目标都进入同步放大复核；保存后自动打包原图 ROI、候选/最终掩膜、分歧层、处置结论和 SHA-256 清单，把人工纠错连接到下一轮数据治理与模型训练。</span><span data-en class="hidden-lang">Each yellow disagreement target enters synchronized review. Saving automatically packages source ROIs, proposal/final masks, disagreement layers, dispositions, and a SHA-256 manifest, connecting human correction to the next governed data and training cycle.</span></p>
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
            <div><h2><span data-zh>选择一次，自动开始</span><span data-en class="hidden-lang">Choose once, start automatically</span></h2><p class="subcopy">JPEG · PNG · WebP · ≤ 15 MiB · ≤ 20 MP</p></div>
            <span class="step">01 · UPLOAD + AUTO</span>
          </div>
          <div class="upload-row">
            <label class="file-label">
              <input id="source-input" type="file" accept="image/jpeg,image/png,image/webp">
              <span id="file-title" class="file-title"><span data-zh>点击选择道路图片</span><span data-en class="hidden-lang">Click to choose a road image</span></span>
              <span id="file-meta" class="file-meta"><span data-zh>图片不会发送到互联网</span><span data-en class="hidden-lang">The image never leaves this machine</span></span>
            </label>
            <button id="replace-button" class="secondary-button" type="button" disabled><span data-zh>重新选择</span><span data-en class="hidden-lang">Replace</span></button>
          </div>
          <div class="pipeline-rail" aria-label="Automatic workflow status">
            <span id="stage-upload" class="pipeline-stage"><span data-zh>读取图片</span><span data-en class="hidden-lang">Load image</span></span>
            <span id="stage-detect" class="pipeline-stage"><span data-zh>检测 + 掩膜</span><span data-en class="hidden-lang">Detect + mask</span></span>
            <span id="stage-draft" class="pipeline-stage"><span data-zh>像素量测草稿</span><span data-en class="hidden-lang">Pixel draft</span></span>
            <span id="stage-review" class="pipeline-stage"><span data-zh>人工复核保存</span><span data-en class="hidden-lang">Review + save</span></span>
          </div>
        </div>

        <div id="inspection-section" class="section hidden">
          <div class="section-head">
            <div><h2><span data-zh>自动检测、风险与可靠性</span><span data-en class="hidden-lang">Automatic detection, risk, and reliability</span></h2><p id="inspection-meta" class="subcopy"><span data-zh>目标检测与多视图可靠性在本机自动运行。</span><span data-en class="hidden-lang">Detection and multi-view reliability run automatically on-device.</span></p></div>
            <span class="step">AUTO · DETECT</span>
          </div>
          <div id="inspection-loading" class="inspection-loading"><span class="spinner" aria-hidden="true"></span><span id="inspection-loading-text"><span data-zh>正在通过 MPS 运行三视图检测与可靠性分析…</span><span data-en class="hidden-lang">Running three-view detection and reliability analysis on MPS…</span></span></div>
          <div id="inspection-result" class="hidden">
            <div class="inspection-overview">
              <div class="inspection-visual"><img id="inspection-image" alt="Automatic road-damage detections"></div>
              <aside class="inspection-summary">
                <strong id="inspection-score" class="inspection-score">— <small>/ 100</small></strong>
                <div class="badges"><span id="inspection-risk-badge" class="badge">—</span><span id="inspection-evidence-badge" class="badge">—</span></div>
                <p id="inspection-recommendation" class="inspection-recommendation">—</p>
                <p id="inspection-record" class="inspection-record">—</p>
              </aside>
            </div>
            <div id="inspection-class-grid" class="inspection-grid"></div>
            <div class="inspection-evidence-grid">
              <section class="inspection-evidence"><h3><span data-zh>证据质量</span><span data-en class="hidden-lang">Evidence quality</span></h3><div id="inspection-evidence"></div><div id="inspection-flags" class="inspection-flags"></div></section>
              <section class="inspection-evidence"><h3><span data-zh>多视图可靠性</span><span data-en class="hidden-lang">Multi-view reliability</span></h3><div id="inspection-reliability"></div><div id="inspection-reliability-flags" class="inspection-flags"></div></section>
            </div>
            <section class="narrative-panel">
              <div class="narrative-head"><div><h3><span data-zh>本地 AI 巡检说明</span><span data-en class="hidden-lang">Local AI inspection narrative</span></h3><p id="narrative-meta" class="subcopy"><span data-zh>仅使用结构化结果，不上传图片。</span><span data-en class="hidden-lang">Uses structured results only; the image is not uploaded.</span></p></div><button id="narrative-button" class="tool-button" type="button" disabled><span data-zh>生成双语说明</span><span data-en class="hidden-lang">Generate narrative</span></button></div>
              <div id="narrative-content" class="narrative-content hidden"><strong id="narrative-summary">—</strong><div id="narrative-details"></div><p id="narrative-limitation">—</p></div>
            </section>
            <details><summary><span data-zh>查看检测明细</span><span data-en class="hidden-lang">View detection details</span></summary><div class="detection-table-wrap"><table class="detection-table"><thead><tr><th>#</th><th><span data-zh>类别</span><span data-en class="hidden-lang">Class</span></th><th><span data-zh>置信度</span><span data-en class="hidden-lang">Confidence</span></th><th>Box</th></tr></thead><tbody id="inspection-detections"></tbody></table></div><p id="inspection-empty" class="subcopy hidden"><span data-zh>没有检测框不代表没有缺陷，仍须人工复核绿色掩膜。</span><span data-en class="hidden-lang">No boxes does not prove no damage; the green mask still requires review.</span></p></details>
          </div>
        </div>

        <div class="section">
          <div class="section-head">
            <div><h2><span data-zh>复核并修正自动掩膜</span><span data-en class="hidden-lang">Review and correct the automatic mask</span></h2><p class="subcopy"><span data-zh>绿色是当前候选，黄色是三档灵敏度分歧热点；先检查黄色区域，再用画笔补漏、橡皮删错。热点不是概率，检测框也不会被冒充为掩膜。</span><span data-en class="hidden-lang">Green is the current proposal; yellow marks disagreement across three sensitivity settings. Review yellow areas first, then add misses or erase errors. Hotspots are not probabilities, and detector boxes are never treated as masks.</span></p></div>
            <span class="step">02 · AUTO MASK + REVIEW</span>
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
            <button id="hotspot-toggle" class="tool-button hotspot active" type="button" disabled><span data-zh>显示黄色复核热点</span><span data-en class="hidden-lang">Show yellow review hotspots</span></button>
            <label class="brush-control"><span><span data-zh>笔宽</span><span data-en class="hidden-lang">Brush</span> <strong id="brush-value">18</strong> px</span><input id="brush-size" type="range" min="2" max="100" value="18" disabled></label>
            <label class="brush-control proposal-control"><span><span data-zh>建议灵敏度</span><span data-en class="hidden-lang">Proposal sensitivity</span> <strong id="proposal-sensitivity-value">55</strong>%</span><input id="proposal-sensitivity" type="range" min="0" max="1" step="0.05" value="0.55" disabled></label>
          </div>
          <section id="hotspot-review" class="hotspot-review hidden" aria-live="polite">
            <div class="hotspot-review-head">
              <strong class="hotspot-review-title"><span data-zh>智能复核队列</span><span data-en class="hidden-lang">Ranked review queue</span></strong>
              <span id="hotspot-progress" class="hotspot-review-progress">—</span>
            </div>
            <div class="hotspot-review-body">
              <div>
                <div class="hotspot-review-actions">
                  <button id="hotspot-previous" class="tool-button" type="button"><span data-zh>上一个</span><span data-en class="hidden-lang">Previous</span></button>
                  <button id="hotspot-next" class="tool-button" type="button"><span data-zh>下一个</span><span data-en class="hidden-lang">Next</span></button>
                  <button id="hotspot-reviewed" class="tool-button" type="button"><span data-zh>标记已检查</span><span data-en class="hidden-lang">Mark inspected</span></button>
                </div>
                <p id="hotspot-detail" class="hotspot-review-detail">—</p>
                <div class="hotspot-review-track" aria-hidden="true"><span id="hotspot-progress-bar" class="hotspot-review-bar"></span></div>
                <p class="hotspot-loupe-help"><span data-zh>放大窗与原图使用同一像素坐标；画笔会自动记录“漏检已补画”，橡皮记录“误检已删除”，你仍可手动改结论。</span><span data-en class="hidden-lang">The loupe shares original-image coordinates. Brush records “missed crack added” and Eraser records “false positive removed” automatically; you can still override the decision.</span></p>
                <div class="hotspot-decision">
                  <p class="hotspot-decision-title"><span data-zh>记录复核处置</span><span data-en class="hidden-lang">Record review disposition</span></p>
                  <div class="hotspot-decision-grid">
                    <button id="decision-accept" class="hotspot-decision-button" type="button" data-disposition="accepted_as_proposed"><span data-zh>接受当前候选</span><span data-en class="hidden-lang">Accept proposal</span></button>
                    <button id="decision-remove" class="hotspot-decision-button" type="button" data-disposition="false_positive_removed"><span data-zh>误检已删除</span><span data-en class="hidden-lang">False positive removed</span></button>
                    <button id="decision-add" class="hotspot-decision-button" type="button" data-disposition="missed_crack_added"><span data-zh>漏检已补画</span><span data-en class="hidden-lang">Missed crack added</span></button>
                    <button id="decision-defer" class="hotspot-decision-button defer" type="button" data-disposition="deferred_for_follow_up"><span data-zh>暂缓，等待跟进</span><span data-en class="hidden-lang">Defer follow-up</span></button>
                  </div>
                  <label class="hotspot-note" for="hotspot-note"><span data-zh>可选备注（最多 160 字）</span><span data-en class="hidden-lang">Optional note (160 characters maximum)</span><input id="hotspot-note" type="text" maxlength="160" autocomplete="off"></label>
                  <p id="hotspot-decision-state" class="hotspot-decision-state">—</p>
                </div>
              </div>
              <div class="hotspot-loupe-shell">
                <canvas id="hotspot-loupe" width="640" height="360" tabindex="0" aria-label="Magnified hotspot mask editor"></canvas>
                <span id="hotspot-loupe-scale" class="hotspot-loupe-scale">—</span>
              </div>
            </div>
          </section>
          <p id="proposal-state" class="subcopy"><span data-zh>上传图片后自动生成可编辑底稿；提交量测前必须人工复核。</span><span data-en class="hidden-lang">An editable proposal is generated automatically after upload; human review is required before metrology.</span></p>
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
            <button id="measure-button" class="primary-button" type="button" disabled><span data-zh>保存人工复核量测</span><span data-en class="hidden-lang">Save reviewed measurement</span></button>
          </div>
          <p id="status" class="status" aria-live="polite"></p>
        </div>
      </section>

      <aside class="results" aria-live="polite">
        <section id="placeholder" class="card placeholder">
          <div><div class="placeholder-mark" aria-hidden="true">μ</div><strong><span data-zh>量测结果将在这里出现</span><span data-en class="hidden-lang">Measurements appear here</span></strong><p><span data-zh>上传图片后先复核自动绿色掩膜，再选择标定方式并运行量测。</span><span data-en class="hidden-lang">Upload an image, review the automatic green mask, choose calibration, and run metrology.</span></p></div>
        </section>
        <section id="result" class="card result-card hidden">
          <div class="artifact-frame"><img id="artifact-image" alt="Metrology artifact"></div>
          <div id="artifact-tabs" class="artifact-tabs"></div>
          <div class="result-summary">
            <div class="result-heading"><div><h2><span data-zh>裂缝几何与拓扑</span><span data-en class="hidden-lang">Crack geometry and topology</span></h2><p id="run-id" class="subcopy">—</p></div><span id="mode-badge" class="mode-badge">—</span></div>
            <p id="review-state" class="review-state draft">—</p>
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
            <div id="feedback-panel" class="utility-result hidden">
              <strong><span data-zh>主动学习反馈包已就绪</span><span data-en class="hidden-lang">Active-learning feedback package ready</span></strong>
              <p><span data-zh>包含已处置热点的原图 ROI、候选掩膜、最终掩膜、分歧层和带 SHA-256 的清单，仅保存在本机。</span><span data-en class="hidden-lang">Contains source ROIs, proposal masks, final masks, disagreement layers, and a SHA-256 manifest for dispositioned hotspots; stored locally only.</span></p>
              <a id="feedback-download" class="download-link" href="" download><span data-zh>下载反馈 ZIP</span><span data-en class="hidden-lang">Download feedback ZIP</span></a>
            </div>
            <div class="practical-grid">
              <section class="utility-panel">
                <h3><span data-zh>材料与成本规划</span><span data-en class="hidden-lang">Material and cost planning</span></h3>
                <p id="plan-note" class="subcopy"><span data-zh>使用标定长度和施工假设估算密封材料。</span><span data-en class="hidden-lang">Estimate sealant from calibrated length and work assumptions.</span></p>
                <div class="utility-fields">
                  <div class="field"><label for="route-width"><span data-zh>开槽宽度 mm</span><span data-en class="hidden-lang">Route width mm</span></label><input id="route-width" type="number" min="0.1" max="200" step="0.1" value="10"></div>
                  <div class="field"><label for="route-depth"><span data-zh>开槽深度 mm</span><span data-en class="hidden-lang">Route depth mm</span></label><input id="route-depth" type="number" min="0.1" max="200" step="0.1" value="10"></div>
                  <div class="field"><label for="waste-percent"><span data-zh>损耗率 %</span><span data-en class="hidden-lang">Waste %</span></label><input id="waste-percent" type="number" min="0" max="200" step="0.1" value="10"></div>
                  <div class="field"><label for="unit-cost"><span data-zh>每升单价（可选）</span><span data-en class="hidden-lang">Cost per litre (optional)</span></label><input id="unit-cost" type="number" min="0" step="0.01" placeholder="—"></div>
                </div>
                <button id="plan-button" class="utility-button" type="button" disabled><span data-zh>生成材料计划</span><span data-en class="hidden-lang">Create material plan</span></button>
                <div id="plan-result" class="utility-result hidden"></div>
              </section>
              <section class="utility-panel">
                <h3><span data-zh>多期裂缝增长对比</span><span data-en class="hidden-lang">Longitudinal crack comparison</span></h3>
                <p class="subcopy"><span data-zh>选择同一路段的旧标定记录；阈值只是人工复核触发器。</span><span data-en class="hidden-lang">Choose an older calibrated run of the same area; thresholds only trigger review.</span></p>
                <div class="utility-fields">
                  <div class="field" style="grid-column: 1 / -1"><label for="baseline-run"><span data-zh>基线记录</span><span data-en class="hidden-lang">Baseline run</span></label><select id="baseline-run"><option value="">—</option></select></div>
                  <div class="field"><label for="elapsed-days"><span data-zh>间隔天数</span><span data-en class="hidden-lang">Elapsed days</span></label><input id="elapsed-days" type="number" min="0.1" step="0.1" value="30"></div>
                  <div class="field"><label for="match-tolerance"><span data-zh>空间容差 mm</span><span data-en class="hidden-lang">Spatial tolerance mm</span></label><input id="match-tolerance" type="number" min="0" max="100" step="0.1" value="5"></div>
                  <div class="field"><label for="length-threshold"><span data-zh>长度增长阈值 %</span><span data-en class="hidden-lang">Length threshold %</span></label><input id="length-threshold" type="number" min="0" step="0.1" value="10"></div>
                  <div class="field"><label for="width-threshold"><span data-zh>P95 宽度阈值 %</span><span data-en class="hidden-lang">P95 width threshold %</span></label><input id="width-threshold" type="number" min="0" step="0.1" value="10"></div>
                </div>
                <button id="compare-button" class="utility-button" type="button" disabled><span data-zh>对比增长</span><span data-en class="hidden-lang">Compare growth</span></button>
                <div id="comparison-result" class="utility-result hidden"></div>
                <div id="comparison-map" class="change-map hidden">
                  <img id="change-map-image" alt="Calibrated spatial crack change map">
                  <div class="change-legend">
                    <span class="legend-item"><span class="legend-dot legend-stable"></span><span data-zh>容差内稳定</span><span data-en class="hidden-lang">Stable</span></span>
                    <span class="legend-item"><span class="legend-dot legend-added"></span><span data-zh>疑似新增</span><span data-en class="hidden-lang">Suspected added</span></span>
                    <span class="legend-item"><span class="legend-dot legend-missing"></span><span data-zh>疑似消失</span><span data-en class="hidden-lang">Suspected missing</span></span>
                  </div>
                </div>
              </section>
            </div>
            <details><summary><span data-zh>查看完整 measurement.json</span><span data-en class="hidden-lang">View complete measurement.json</span></summary><pre id="json-output"></pre></details>
          </div>
        </section>
      </aside>
    </div>
  </main>
  <footer class="shell">UrbanVision-Risk v4.7 · Active-Learning Feedback + Audited Review · Fully local / 完全本地</footer>

  <script>
    (() => {
      const byId = (id) => document.getElementById(id);
      const editor = byId("editor-canvas");
      const editorContext = editor.getContext("2d");
      const maskCanvas = document.createElement("canvas");
      const maskContext = maskCanvas.getContext("2d");
      const proposalCanvas = document.createElement("canvas");
      const proposalContext = proposalCanvas.getContext("2d");
      const hotspotCanvas = document.createElement("canvas");
      const hotspotContext = hotspotCanvas.getContext("2d");
      const tintCanvas = document.createElement("canvas");
      const tintContext = tintCanvas.getContext("2d");
      const hotspotLoupe = byId("hotspot-loupe");
      const hotspotLoupeContext = hotspotLoupe.getContext("2d");
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
      let latestPlan = null;
      let latestComparison = null;
      let latestProposal = null;
      let latestInspection = null;
      let latestNarrative = null;
      let activeProposalId = null;
      let proposalSuppressed = false;
      let reviewHotspotsVisible = true;
      let hotspotComponents = [];
      let reviewedHotspotIds = new Set();
      let hotspotDecisions = new Map();
      let hotspotDraftNotes = new Map();
      let activeHotspotIndex = -1;
      let hotspotLoupeViewport = null;
      let loupeDrawing = false;
      let loupeActiveStroke = null;
      let hoverPoint = null;
      let sourceGeneration = 0;
      let maskDirty = false;
      let reviewProgressDirty = false;
      let measurementOperationCount = 0;
      let pipelineStage = "idle";

      const text = {
        zh: {
          choose: "点击选择道路图片",
          private: "图片不会发送到互联网",
          ready: "原图已就绪，自动检测与自动掩膜正在并行运行。",
          pipelineComplete: "自动检测、绿色掩膜和像素量测草稿已完成；请人工复核后保存。",
          pipelinePartial: "自动流水线部分完成；请检查上方结果并人工补充掩膜。",
          inspectionRunning: "正在通过 MPS 运行三视图检测与可靠性分析…",
          inspectionComplete: "自动检测与可靠性分析完成。",
          inspectionFailed: "自动检测失败；掩膜与手工量测仍可继续。",
          detections: "个检测",
          evidence: "证据",
          mean: "平均置信度",
          minimum: "最低置信度",
          views: "推理视图",
          consensus: "共识 / 分歧簇",
          stability: "平均定位稳定性",
          uncertainty: "平均不确定性",
          activeLearning: "主动学习优先级",
          narrativeReady: "可以生成本地双语说明。",
          narrativeLoading: "正在通过本地 Ollama 或审计模板生成说明…",
          narrativeTemplate: "审计模板 · 完全本地",
          narrativeOllama: "Ollama 本地模型",
          narrativeError: "本地说明生成失败，请检查终端日志。",
          drawingRequired: "请先选择原图并绘制裂缝掩膜。",
          proposalIdle: "上传图片后自动生成可编辑底稿；提交量测前必须人工复核。",
          proposalRunning: "正在本机运行多尺度暗脊与形态学集成…",
          proposalReady: "候选底稿已载入；请用画笔和橡皮人工复核。",
          proposalEmpty: "没有找到可靠候选；请手动画笔标注或提高建议灵敏度。",
          autoDrafting: "自动掩膜已完成，正在生成像素量测草稿…",
          autoDraftComplete: "像素量测草稿已生成；它还没有经过人工复核。",
          autoDraftFailed: "自动量测草稿生成失败；可以人工修正后再保存。",
          draftBadge: "自动草稿 · 仅像素",
          draftState: "这是自动候选生成的像素量测草稿，尚未经过人工复核，不能作为真实尺寸或安全结论。",
          editedState: "绿色掩膜已有尚未保存的人工修改；右侧仍显示上一次自动草稿。",
          reviewedState: "这是已保存的人工复核版本；真实尺寸仍只在有效标定后成立。",
          demoState: "这是确定性算法演示，不代表人工复核或现场精度验证。",
          confirmReviewed: "确认并保存复核量测",
          saveEdited: "保存修正后的量测",
          saveAgain: "重新保存量测",
          humanAdded: "人工增加像素",
          humanRemoved: "人工删除像素",
          proposalIou: "候选—最终 IoU",
          changedRatio: "人工修改画面占比",
          reviewHotspots: "黄色复核热点",
          sensitivityDisagreement: "候选分歧",
          showHotspots: "显示黄色复核热点",
          hideHotspots: "隐藏黄色复核热点",
          inspectedHotspots: "已检查热点",
          decidedHotspots: "已记录处置",
          rankedQueue: "优先队列",
          priorityCoverage: "优先影响覆盖",
          markInspected: "标记已检查",
          markedInspected: "取消已检查",
          saveReviewProgress: "保存复核进度",
          reviewProgressState: "热点检查进度尚未保存；保存后会进入不可覆盖的量测证据。",
          awaitingDecision: "尚未记录处置结论。",
          decisionRecorded: "已记录",
          decisionCoverage: "处置优先级覆盖",
          feedbackItems: "主动学习反馈样本",
          loupeToolRequired: "放大窗只用于画笔或橡皮；请先切换工具。",
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
          quad: "标定区域画面占比",
          planReady: "使用标定长度和施工假设估算密封材料。",
          planPixel: "材料计划需要有效的真实平面标定；仅像素模式不能估算升数。",
          planRunning: "正在生成不可覆盖的材料计划…",
          planComplete: "材料计划已保存",
          treatmentLength: "处理长度",
          procurementVolume: "建议采购体积",
          estimatedCost: "估算材料成本",
          compareRunning: "正在对比两次标定量测…",
          compareComplete: "增长对比已保存",
          noBaseline: "还没有另一条可对比的标定记录。",
          lengthChange: "网络长度变化",
          widthChange: "P95 宽度变化",
          dailyGrowth: "每日长度变化",
          addedArea: "疑似新增面积",
          missingArea: "疑似消失面积",
          alignmentQuality: "物理对齐质量",
          strongAlignment: "强",
          acceptableAlignment: "可接受",
          reviewRequired: "变化超过用户阈值，需要人工复核",
          withinThreshold: "变化未超过用户阈值",
          downloadJson: "下载审计 JSON"
        },
        en: {
          choose: "Click to choose a road image",
          private: "The image never leaves this machine",
          ready: "Source ready; automatic detection and mask proposal are running in parallel.",
          pipelineComplete: "Detection, the green mask, and a pixel-metrology draft are ready; review and save.",
          pipelinePartial: "The automatic pipeline partially completed; inspect the result and correct the mask.",
          inspectionRunning: "Running three-view detection and reliability analysis on MPS…",
          inspectionComplete: "Automatic detection and reliability analysis complete.",
          inspectionFailed: "Automatic detection failed; mask review and manual metrology can continue.",
          detections: "detections",
          evidence: "Evidence",
          mean: "Mean confidence",
          minimum: "Minimum confidence",
          views: "Inference views",
          consensus: "Consensus / disputed",
          stability: "Mean localization stability",
          uncertainty: "Mean uncertainty",
          activeLearning: "Active-learning priority",
          narrativeReady: "Ready to generate a local bilingual narrative.",
          narrativeLoading: "Generating through local Ollama or the audited template…",
          narrativeTemplate: "Audited template · fully local",
          narrativeOllama: "Local Ollama model",
          narrativeError: "Local narrative generation failed; check the terminal log.",
          drawingRequired: "Choose a source image and draw a crack mask first.",
          proposalIdle: "An editable proposal is generated automatically after upload; human review is required before metrology.",
          proposalRunning: "Running the multi-scale dark-ridge and morphology ensemble locally…",
          proposalReady: "The proposal is loaded; review it with the brush and eraser.",
          proposalEmpty: "No reliable candidate was found; draw manually or increase proposal sensitivity.",
          autoDrafting: "The automatic mask is ready; creating a pixel-metrology draft…",
          autoDraftComplete: "The pixel-metrology draft is ready; it has not been human-reviewed.",
          autoDraftFailed: "The automatic measurement draft failed; correct the mask and save manually.",
          draftBadge: "Auto draft · pixel only",
          draftState: "This pixel measurement comes from the automatic proposal and has not been human-reviewed. It is not a physical-size or safety conclusion.",
          editedState: "The green mask has unsaved human changes; the right side still shows the previous automatic draft.",
          reviewedState: "This is a saved human-reviewed version. Physical dimensions still require valid calibration.",
          demoState: "This is a deterministic algorithm demo, not human review or field-accuracy validation.",
          confirmReviewed: "Confirm and save review",
          saveEdited: "Save corrected measurement",
          saveAgain: "Save another measurement",
          humanAdded: "Human-added pixels",
          humanRemoved: "Human-removed pixels",
          proposalIou: "Proposal–final IoU",
          changedRatio: "Changed image ratio",
          reviewHotspots: "Yellow review hotspots",
          sensitivityDisagreement: "proposal disagreement",
          showHotspots: "Show yellow review hotspots",
          hideHotspots: "Hide yellow review hotspots",
          inspectedHotspots: "Inspected hotspots",
          decidedHotspots: "Dispositioned",
          rankedQueue: "Priority queue",
          priorityCoverage: "Priority-impact coverage",
          markInspected: "Mark inspected",
          markedInspected: "Undo inspected",
          saveReviewProgress: "Save review progress",
          reviewProgressState: "Hotspot-review progress is not saved yet; saving records it in immutable measurement evidence.",
          awaitingDecision: "No disposition has been recorded yet.",
          decisionRecorded: "Recorded",
          decisionCoverage: "Disposition priority coverage",
          feedbackItems: "Active-learning feedback items",
          loupeToolRequired: "The loupe accepts Brush or Eraser; switch tools first.",
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
          quad: "Calibration image ratio",
          planReady: "Estimate sealant from calibrated length and work assumptions.",
          planPixel: "A material plan needs valid physical calibration; pixel-only mode cannot estimate litres.",
          planRunning: "Creating an immutable material plan…",
          planComplete: "Material plan saved",
          treatmentLength: "Treatment length",
          procurementVolume: "Procurement volume",
          estimatedCost: "Estimated material cost",
          compareRunning: "Comparing two calibrated measurements…",
          compareComplete: "Growth comparison saved",
          noBaseline: "No other calibrated run is available yet.",
          lengthChange: "Network-length change",
          widthChange: "P95-width change",
          dailyGrowth: "Daily length change",
          addedArea: "Suspected added area",
          missingArea: "Suspected missing area",
          alignmentQuality: "Physical alignment quality",
          strongAlignment: "Strong",
          acceptableAlignment: "Acceptable",
          reviewRequired: "Change exceeds the user threshold; human review required",
          withinThreshold: "Change remains within the user threshold",
          downloadJson: "Download audit JSON"
        }
      };
      const t = (key) => text[language][key] || key;
      const priorityLabels = {
        zh: { low: "低优先级", moderate: "中等优先级", high: "高优先级", critical: "严重优先级", review_required: "需要人工复核" },
        en: { low: "Low priority", moderate: "Moderate priority", high: "High priority", critical: "Critical priority", review_required: "Human review required" }
      };
      const evidenceLabels = {
        zh: { not_applicable: "不适用", low: "低", moderate: "中等", high: "高" },
        en: { not_applicable: "N/A", low: "Low", moderate: "Moderate", high: "High" }
      };
      const dispositionLabels = {
        zh: {
          accepted_as_proposed: "接受当前候选",
          false_positive_removed: "误检已删除",
          missed_crack_added: "漏检已补画",
          deferred_for_follow_up: "暂缓，等待跟进"
        },
        en: {
          accepted_as_proposed: "Accept proposal",
          false_positive_removed: "False positive removed",
          missed_crack_added: "Missed crack added",
          deferred_for_follow_up: "Defer follow-up"
        }
      };
      const tierLabels = {
        zh: { low: "低", medium: "中", high: "高", not_applicable: "不适用" },
        en: { low: "Low", medium: "Medium", high: "High", not_applicable: "N/A" }
      };
      const number = (value, digits = 1) => value === null || value === undefined ? "—" : Number(value).toFixed(digits);

      function renderProposalState() {
        if (activeProposalId && latestProposal) {
          const coverage = Number(latestProposal.evidence.selection.coverage_ratio) * 100;
          const guidance = latestProposal.evidence.review_guidance;
          if (guidance) {
            const hotspotRatio = Number(guidance.review_hotspot_image_ratio) * 100;
            const disagreementRatio = guidance.disagreement_ratio_of_union === null ? null : Number(guidance.disagreement_ratio_of_union) * 100;
            const disagreement = disagreementRatio === null ? "—" : `${disagreementRatio.toFixed(2)}%`;
            byId("proposal-state").textContent = `${t("proposalReady")} ${coverage.toFixed(2)}% · ${t("reviewHotspots")} ${hotspotRatio.toFixed(2)}% · ${t("sensitivityDisagreement")} ${disagreement}`;
          } else {
            byId("proposal-state").textContent = `${t("proposalReady")} ${coverage.toFixed(2)}%`;
          }
        } else {
          byId("proposal-state").textContent = t("proposalIdle");
        }
        updateHotspotToggle();
      }

      function updateHotspotToggle() {
        const button = byId("hotspot-toggle");
        const available = Boolean(latestProposal && latestProposal.artifacts && latestProposal.artifacts["review-hotspots.png"]);
        button.disabled = !available || measurementOperationCount > 0;
        button.classList.toggle("active", available && reviewHotspotsVisible);
        button.textContent = available && reviewHotspotsVisible ? t("hideHotspots") : t("showHotspots");
      }

      function renderHotspotReview() {
        const panel = byId("hotspot-review");
        const available = hotspotComponents.length > 0;
        panel.classList.toggle("hidden", !available);
        if (!available) return;
        activeHotspotIndex = Math.max(0, Math.min(activeHotspotIndex, hotspotComponents.length - 1));
        const current = hotspotComponents[activeHotspotIndex];
        const reviewedCount = hotspotComponents.filter((hotspot) => reviewedHotspotIds.has(hotspot.hotspot_id)).length;
        const decidedCount = hotspotComponents.filter((hotspot) => hotspotDecisions.has(hotspot.hotspot_id)).length;
        const totalPriority = hotspotComponents.reduce((sum, hotspot) => sum + Number(hotspot.priority_score || 0), 0);
        const reviewedPriority = hotspotComponents.reduce((sum, hotspot) => reviewedHotspotIds.has(hotspot.hotspot_id) ? sum + Number(hotspot.priority_score || 0) : sum, 0);
        const priorityCoverage = totalPriority > 0 ? reviewedPriority / totalPriority * 100 : 0;
        const guidance = latestProposal && latestProposal.evidence && latestProposal.evidence.review_guidance;
        const totalComponents = guidance && Number(guidance.review_zone_component_count);
        const queueScope = totalComponents ? `${t("rankedQueue")} ${hotspotComponents.length}/${totalComponents} · ` : "";
        byId("hotspot-progress").textContent = `${queueScope}${t("inspectedHotspots")} ${reviewedCount}/${hotspotComponents.length} · ${t("decidedHotspots")} ${decidedCount}/${hotspotComponents.length} · ${t("priorityCoverage")} ${priorityCoverage.toFixed(1)}%`;
        byId("hotspot-progress-bar").style.width = `${priorityCoverage}%`;
        const box = current.bounding_box;
        const overlap = Number(current.candidate_overlap_ratio || 0) * 100;
        byId("hotspot-detail").textContent = language === "zh"
          ? `当前 #${current.rank} · 分歧 ${current.disagreement_pixels} px · 候选重叠 ${overlap.toFixed(1)}% · 区域 ${box.width} × ${box.height} px`
          : `Current #${current.rank} · disagreement ${current.disagreement_pixels} px · proposal overlap ${overlap.toFixed(1)}% · region ${box.width} × ${box.height} px`;
        const busy = measurementOperationCount > 0;
        byId("hotspot-previous").disabled = busy || hotspotComponents.length < 2;
        byId("hotspot-next").disabled = busy || hotspotComponents.length < 2;
        const inspected = reviewedHotspotIds.has(current.hotspot_id);
        const reviewButton = byId("hotspot-reviewed");
        reviewButton.disabled = busy;
        reviewButton.classList.toggle("reviewed", inspected);
        reviewButton.textContent = inspected ? t("markedInspected") : t("markInspected");
        const decision = hotspotDecisions.get(current.hotspot_id);
        document.querySelectorAll(".hotspot-decision-button").forEach((button) => {
          button.disabled = busy;
          button.classList.toggle(
            "selected",
            Boolean(decision && decision.disposition === button.dataset.disposition)
          );
        });
        const noteInput = byId("hotspot-note");
        noteInput.disabled = busy;
        noteInput.value = hotspotDraftNotes.get(current.hotspot_id) || "";
        byId("hotspot-decision-state").textContent = decision
          ? `${t("decisionRecorded")}: ${dispositionLabels[language][decision.disposition]}`
          : t("awaitingDecision");
      }

      function focusHotspot(index) {
        if (!hotspotComponents.length) return;
        activeHotspotIndex = (index + hotspotComponents.length) % hotspotComponents.length;
        reviewHotspotsVisible = true;
        updateHotspotToggle();
        renderHotspotReview();
        renderEditor();
        byId("editor-canvas").scrollIntoView({ behavior: "smooth", block: "center" });
      }

      function calculateLoupeViewport(hotspot) {
        const box = hotspot.bounding_box;
        const aspect = hotspotLoupe.width / hotspotLoupe.height;
        let width = Math.max(72, Number(box.width) * 2.2);
        let height = Math.max(54, Number(box.height) * 2.2);
        if (width / height < aspect) width = height * aspect;
        else height = width / aspect;
        if (width > editor.width) {
          width = editor.width;
          height = width / aspect;
        }
        if (height > editor.height) {
          height = editor.height;
          width = height * aspect;
        }
        const centerX = Number(box.x) + Number(box.width) / 2;
        const centerY = Number(box.y) + Number(box.height) / 2;
        return {
          x: Math.max(0, Math.min(editor.width - width, centerX - width / 2)),
          y: Math.max(0, Math.min(editor.height - height, centerY - height / 2)),
          width,
          height
        };
      }

      function renderHotspotLoupe() {
        hotspotLoupeContext.clearRect(0, 0, hotspotLoupe.width, hotspotLoupe.height);
        const hotspot = hotspotComponents[activeHotspotIndex];
        if (!sourceImage || !hotspot) {
          hotspotLoupeViewport = null;
          byId("hotspot-loupe-scale").textContent = "—";
          return;
        }
        hotspotLoupeViewport = calculateLoupeViewport(hotspot);
        hotspotLoupeContext.imageSmoothingEnabled = true;
        hotspotLoupeContext.imageSmoothingQuality = "high";
        hotspotLoupeContext.drawImage(
          editor,
          hotspotLoupeViewport.x,
          hotspotLoupeViewport.y,
          hotspotLoupeViewport.width,
          hotspotLoupeViewport.height,
          0,
          0,
          hotspotLoupe.width,
          hotspotLoupe.height
        );
        const zoom = hotspotLoupe.width / hotspotLoupeViewport.width;
        byId("hotspot-loupe-scale").textContent = `${zoom.toFixed(1)}× · ${Math.round(hotspotLoupeViewport.width)} × ${Math.round(hotspotLoupeViewport.height)} px`;
      }

      function loupeCanvasPosition(event) {
        if (!hotspotLoupeViewport) return null;
        const rectangle = hotspotLoupe.getBoundingClientRect();
        const loupeX = Math.max(0, Math.min(hotspotLoupe.width, (event.clientX - rectangle.left) * hotspotLoupe.width / rectangle.width));
        const loupeY = Math.max(0, Math.min(hotspotLoupe.height, (event.clientY - rectangle.top) * hotspotLoupe.height / rectangle.height));
        return {
          x: hotspotLoupeViewport.x + loupeX / hotspotLoupe.width * hotspotLoupeViewport.width,
          y: hotspotLoupeViewport.y + loupeY / hotspotLoupe.height * hotspotLoupeViewport.height
        };
      }

      function recordHotspotDecision(disposition) {
        const hotspot = hotspotComponents[activeHotspotIndex];
        if (!hotspot) return;
        const note = (hotspotDraftNotes.get(hotspot.hotspot_id) || "").trim();
        hotspotDecisions.set(hotspot.hotspot_id, {
          hotspot_id: hotspot.hotspot_id,
          disposition,
          ...(note ? { note } : {})
        });
        reviewedHotspotIds.add(hotspot.hotspot_id);
        reviewProgressDirty = true;
        setPipeline("review");
        renderHotspotReview();
        updateReviewUI();
      }

      function setStatus(message, error = false) {
        byId("status").textContent = message;
        byId("status").classList.toggle("error", error);
      }

      function setPipeline(stage) {
        pipelineStage = stage;
        const order = ["upload", "detect", "draft", "review"];
        const activeIndex = { idle: -1, upload: 0, detect: 1, draft: 2, review: 3, saved: 4 }[stage] ?? -1;
        order.forEach((name, index) => {
          const item = byId(`stage-${name}`);
          item.classList.toggle("complete", index < activeIndex || stage === "saved");
          item.classList.toggle("active", index === activeIndex && stage !== "saved");
        });
      }

      function resultReviewState() {
        const inputEvidence = latestResult && latestResult.measurement && latestResult.measurement.run && latestResult.measurement.run.input_evidence;
        if (inputEvidence && inputEvidence.kind === "deterministic_web_demo") return "demo";
        return inputEvidence && inputEvidence.review_state ? inputEvidence.review_state : "human_reviewed";
      }

      function updateReviewUI() {
        const button = byId("measure-button");
        if (!latestResult) {
          button.textContent = t("confirmReviewed");
          return;
        }
        if (maskDirty) button.textContent = t("saveEdited");
        else if (reviewProgressDirty) button.textContent = t("saveReviewProgress");
        else if (latestResult && resultReviewState() === "automatic_draft") button.textContent = t("confirmReviewed");
        else button.textContent = t("saveAgain");
        const state = byId("review-state");
        const resultState = resultReviewState();
        const reviewed = resultState === "human_reviewed";
        const pending = maskDirty || reviewProgressDirty;
        state.className = `review-state ${reviewed && !pending ? "reviewed" : "draft"}`;
        state.textContent = maskDirty ? t("editedState") : reviewProgressDirty ? t("reviewProgressState") : (resultState === "demo" ? t("demoState") : (reviewed ? t("reviewedState") : t("draftState")));
      }

      function markMaskDirty() {
        maskDirty = true;
        setPipeline("review");
        updateReviewUI();
      }

      function addInspectionRow(container, label, value) {
        const row = document.createElement("div");
        row.className = "inspection-evidence-row";
        const name = document.createElement("span");
        name.textContent = label;
        const result = document.createElement("strong");
        result.textContent = value ?? "—";
        row.append(name, result);
        container.appendChild(row);
      }

      function renderInspection(payload) {
        latestInspection = payload;
        const prediction = payload.prediction || {};
        const detections = prediction.detections || [];
        const risk = payload.risk || {};
        const evidence = risk.evidence || {};
        const reliability = prediction.reliability || {};
        const reliabilitySummary = reliability.summary || {};
        const reviewRequired = risk.decision_status === "review_required" || risk.review_required === true;
        const riskLevel = reviewRequired ? "review_required" : (risk.risk_level || "review_required");
        const evidenceQuality = evidence.quality || "not_applicable";

        byId("inspection-loading").classList.add("hidden");
        byId("inspection-result").classList.remove("hidden");
        byId("inspection-image").src = `${payload.annotated_url}?v=${encodeURIComponent(payload.inspection_id)}`;
        byId("inspection-score").innerHTML = `${reviewRequired ? "—" : number(risk.risk_score)} <small>/ 100</small>`;
        byId("inspection-risk-badge").className = `badge badge-${riskLevel}`;
        byId("inspection-risk-badge").textContent = priorityLabels[language][riskLevel] || riskLevel;
        byId("inspection-evidence-badge").className = `badge badge-${evidenceQuality}`;
        byId("inspection-evidence-badge").textContent = `${t("evidence")}: ${evidenceLabels[language][evidenceQuality] || evidenceQuality}`;
        byId("inspection-recommendation").textContent = risk.recommendation ? risk.recommendation[language] : t("inspectionComplete");
        byId("inspection-record").textContent = `ID ${payload.inspection_id} · ${payload.source_filename || "—"}`;
        const dimensions = prediction.image_dimensions || {};
        byId("inspection-meta").textContent = `${dimensions.width || "—"} × ${dimensions.height || "—"} px · ${detections.length} ${t("detections")}`;

        const classes = byId("inspection-class-grid");
        classes.replaceChildren();
        const classItems = [...(risk.class_breakdown || []), ...(risk.auxiliary_observations || [])];
        classItems.forEach((item) => {
          const card = document.createElement("div");
          card.className = "inspection-class";
          const code = document.createElement("span");
          code.className = "inspection-class-code";
          code.textContent = item.code;
          const line = document.createElement("div");
          line.className = "inspection-class-line";
          const name = document.createElement("span");
          name.className = "inspection-class-name";
          name.textContent = language === "zh" ? item.name_zh : item.name_en;
          const count = document.createElement("strong");
          count.className = "inspection-class-count";
          count.textContent = String(item.count);
          line.append(name, count);
          card.append(code, line);
          classes.appendChild(card);
        });

        const evidenceBox = byId("inspection-evidence");
        evidenceBox.replaceChildren();
        addInspectionRow(evidenceBox, t("mean"), number(evidence.mean_detection_confidence, 3));
        addInspectionRow(evidenceBox, t("minimum"), number(evidence.minimum_detection_confidence, 3));
        const flags = byId("inspection-flags");
        flags.replaceChildren();
        (risk.audit_flags || []).forEach((item) => {
          const flag = document.createElement("p");
          flag.className = "inspection-flag";
          flag.textContent = `⚑ ${item[language]}`;
          flags.appendChild(flag);
        });

        const reliabilityBox = byId("inspection-reliability");
        reliabilityBox.replaceChildren();
        addInspectionRow(reliabilityBox, t("views"), reliability.view_count);
        addInspectionRow(reliabilityBox, t("consensus"), `${reliabilitySummary.accepted_cluster_count ?? "—"} / ${reliabilitySummary.disputed_cluster_count ?? "—"}`);
        addInspectionRow(reliabilityBox, t("stability"), number(reliabilitySummary.mean_stability, 3));
        addInspectionRow(reliabilityBox, t("uncertainty"), number(reliabilitySummary.mean_uncertainty, 3));
        addInspectionRow(reliabilityBox, t("activeLearning"), `${number(reliabilitySummary.active_learning_priority)} · ${tierLabels[language][reliabilitySummary.active_learning_tier] || "—"}`);
        const reliabilityFlags = byId("inspection-reliability-flags");
        reliabilityFlags.replaceChildren();
        if (reliabilitySummary.review_recommended) {
          const flag = document.createElement("p");
          flag.className = "inspection-flag";
          flag.textContent = language === "zh" ? "⚑ 多视图证据不稳定，已进入人工复核与主动学习队列。" : "⚑ Unstable multi-view evidence: routed to human review and active learning.";
          reliabilityFlags.appendChild(flag);
        }

        const rows = byId("inspection-detections");
        rows.replaceChildren();
        byId("inspection-empty").classList.toggle("hidden", detections.length !== 0);
        detections.forEach((item, index) => {
          const row = document.createElement("tr");
          [String(index + 1), `${item.code} · ${language === "zh" ? item.name_zh : item.name_en}`, number(item.confidence, 3), (item.bbox_xyxy || []).map((value) => Math.round(value)).join(", ")].forEach((value) => {
            const cell = document.createElement("td");
            cell.textContent = value;
            row.appendChild(cell);
          });
          rows.appendChild(row);
        });
        if (!latestNarrative) {
          byId("narrative-content").classList.add("hidden");
          byId("narrative-button").disabled = false;
          byId("narrative-meta").textContent = t("narrativeReady");
        }
      }

      function renderNarrative(payload) {
        latestNarrative = payload;
        const generator = payload.generator || {};
        byId("narrative-meta").textContent = generator.mode === "ollama" ? `${t("narrativeOllama")} · ${generator.model}` : t("narrativeTemplate");
        byId("narrative-summary").textContent = payload.summary[language];
        const details = byId("narrative-details");
        details.replaceChildren();
        [payload.observations || [], payload.actions || []].forEach((items) => {
          const list = document.createElement("ul");
          items.forEach((item) => {
            const row = document.createElement("li");
            row.textContent = item[language];
            list.appendChild(row);
          });
          details.appendChild(list);
        });
        byId("narrative-limitation").textContent = payload.limitation[language];
        byId("narrative-content").classList.remove("hidden");
        byId("narrative-button").disabled = true;
      }

      async function generateNarrative() {
        if (!latestInspection) return;
        byId("narrative-button").disabled = true;
        byId("narrative-meta").textContent = t("narrativeLoading");
        try {
          const inspectionId = encodeURIComponent(latestInspection.inspection_id);
          const response = await fetch(`/api/inspections/${inspectionId}/narrative`, { method: "POST" });
          const payload = await response.json();
          if (!response.ok) throw payload.error || payload;
          renderNarrative(payload);
        } catch (error) {
          const message = error && (language === "zh" ? error.message_zh : error.message_en);
          byId("narrative-meta").textContent = message || t("narrativeError");
          byId("narrative-button").disabled = false;
        }
      }

      async function runAutomaticInspection(file, generation) {
        byId("inspection-section").classList.remove("hidden");
        byId("inspection-result").classList.add("hidden");
        byId("inspection-loading").classList.remove("hidden");
        byId("inspection-loading-text").textContent = t("inspectionRunning");
        const form = new FormData();
        form.append("image", file, file.name);
        const response = await fetch("/api/inspect", { method: "POST", body: form });
        const payload = await response.json();
        if (!response.ok) throw payload.error || payload;
        if (generation !== sourceGeneration) return false;
        latestNarrative = null;
        renderInspection(payload);
        return true;
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
        if (latestPlan) renderPlan(latestPlan);
        if (latestComparison) renderComparison(latestComparison);
        if (latestInspection) renderInspection(latestInspection);
        if (latestNarrative) renderNarrative(latestNarrative);
        renderProposalState();
        renderHotspotReview();
        setPipeline(pipelineStage);
        updateReviewUI();
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
        maskContext.clearRect(0, 0, maskCanvas.width, maskCanvas.height);
        proposalContext.clearRect(0, 0, proposalCanvas.width, proposalCanvas.height);
        hotspotContext.clearRect(0, 0, hotspotCanvas.width, hotspotCanvas.height);
        strokes = [];
        activeStroke = null;
        activeProposalId = null;
        proposalSuppressed = false;
        latestProposal = null;
        reviewHotspotsVisible = true;
        hotspotComponents = [];
        reviewedHotspotIds = new Set();
        hotspotDecisions = new Map();
        hotspotDraftNotes = new Map();
        activeHotspotIndex = -1;
        hotspotLoupeViewport = null;
        loupeDrawing = false;
        loupeActiveStroke = null;
        hotspotLoupeContext.clearRect(0, 0, hotspotLoupe.width, hotspotLoupe.height);
        byId("hotspot-loupe-scale").textContent = "—";
        maskDirty = false;
        reviewProgressDirty = false;
        renderProposalState();
        renderHotspotReview();
      }

      function drawStroke(context, stroke) {
        if (!stroke.points.length) return;
        context.save();
        context.globalCompositeOperation = stroke.tool === "eraser" ? "destination-out" : "source-over";
        context.strokeStyle = "#fff";
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
        maskContext.clearRect(0, 0, maskCanvas.width, maskCanvas.height);
        if (activeProposalId && !proposalSuppressed) maskContext.drawImage(proposalCanvas, 0, 0);
        strokes.forEach((stroke) => drawStroke(maskContext, stroke));
      }

      function renderEditor() {
        if (!sourceImage) return;
        editorContext.clearRect(0, 0, editor.width, editor.height);
        editorContext.drawImage(sourceImage, 0, 0, editor.width, editor.height);
        if (reviewHotspotsVisible && latestProposal) {
          tintContext.clearRect(0, 0, tintCanvas.width, tintCanvas.height);
          tintContext.globalCompositeOperation = "source-over";
          tintContext.fillStyle = "#ffd34d";
          tintContext.fillRect(0, 0, tintCanvas.width, tintCanvas.height);
          tintContext.globalCompositeOperation = "destination-in";
          tintContext.drawImage(hotspotCanvas, 0, 0);
          tintContext.globalCompositeOperation = "source-over";
          editorContext.save();
          editorContext.globalAlpha = .62;
          editorContext.drawImage(tintCanvas, 0, 0);
          editorContext.restore();
        }
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

        if (activeHotspotIndex >= 0 && hotspotComponents[activeHotspotIndex]) {
          const hotspot = hotspotComponents[activeHotspotIndex];
          const box = hotspot.bounding_box;
          const scale = Math.max(2, Math.min(editor.width, editor.height) / 300);
          const padding = scale * 2.5;
          const x = Math.max(0, box.x - padding);
          const y = Math.max(0, box.y - padding);
          const width = Math.min(editor.width - x, box.width + padding * 2);
          const height = Math.min(editor.height - y, box.height + padding * 2);
          const label = `#${hotspot.rank}`;
          editorContext.save();
          editorContext.setLineDash([scale * 4, scale * 2]);
          editorContext.lineWidth = scale * 2.4;
          editorContext.strokeStyle = "rgba(0, 0, 0, .88)";
          editorContext.strokeRect(x, y, width, height);
          editorContext.lineWidth = scale * 1.2;
          editorContext.strokeStyle = "#ffd34d";
          editorContext.strokeRect(x, y, width, height);
          editorContext.setLineDash([]);
          editorContext.font = `700 ${Math.max(14, scale * 5)}px -apple-system, sans-serif`;
          const labelWidth = editorContext.measureText(label).width + scale * 4;
          const labelHeight = Math.max(18, scale * 7);
          editorContext.fillStyle = "rgba(0, 0, 0, .82)";
          editorContext.fillRect(x, Math.max(0, y - labelHeight), labelWidth, labelHeight);
          editorContext.fillStyle = "#ffd34d";
          editorContext.fillText(label, x + scale * 2, Math.max(labelHeight * .72, y - scale * 1.5));
          editorContext.restore();
        }

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
        if (hoverPoint && tool !== "point") {
          const radius = Number(byId("brush-size").value) / 2;
          editorContext.save();
          editorContext.beginPath();
          editorContext.arc(hoverPoint.x, hoverPoint.y, radius, 0, Math.PI * 2);
          editorContext.lineWidth = Math.max(2, Math.min(editor.width, editor.height) / 500);
          editorContext.strokeStyle = "rgba(0, 0, 0, .9)";
          editorContext.stroke();
          editorContext.beginPath();
          editorContext.arc(hoverPoint.x, hoverPoint.y, radius + editorContext.lineWidth * 1.4, 0, Math.PI * 2);
          editorContext.lineWidth = Math.max(1, editorContext.lineWidth / 2);
          editorContext.strokeStyle = tool === "eraser" ? "#ff9b62" : "#8dffd4";
          editorContext.stroke();
          editorContext.restore();
        }
        renderHotspotLoupe();
      }

      function setTool(nextTool) {
        tool = nextTool;
        ["brush", "eraser", "point"].forEach((name) => byId(`${name}-tool`).classList.toggle("active", name === tool));
        editor.style.cursor = tool === "point" ? "cell" : "crosshair";
        hotspotLoupe.style.cursor = tool === "point" ? "not-allowed" : "crosshair";
      }

      function updateControls() {
        const ready = Boolean(sourceImage);
        const editable = ready && measurementOperationCount === 0;
        ["proposal-sensitivity", "brush-tool", "eraser-tool", "clear-button", "brush-size"].forEach((id) => { byId(id).disabled = !editable; });
        byId("point-tool").disabled = !editable || byId("calibration-mode").value !== "manual";
        byId("undo-button").disabled = !editable || strokes.length === 0;
        byId("replace-button").disabled = !ready;
        const hasMask = (activeProposalId && !proposalSuppressed) || strokes.length > 0;
        byId("measure-button").disabled = !editable || !hasMask;
        hotspotLoupe.setAttribute("aria-disabled", String(!editable || !hotspotComponents.length));
        hotspotLoupe.style.opacity = editable && hotspotComponents.length ? "1" : ".5";
        updateHotspotToggle();
        renderHotspotReview();
        updateReviewUI();
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
        const generation = ++sourceGeneration;
        setPipeline("upload");
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
        if (generation !== sourceGeneration) return;
        if (image.naturalWidth * image.naturalHeight > 20_000_000) {
          setStatus(language === "zh" ? "量测工作台限制为 2000 万像素。" : "The metrology workbench is limited to 20 megapixels.", true);
          return;
        }
        sourceFile = file;
        sourceImage = image;
        editor.width = maskCanvas.width = proposalCanvas.width = hotspotCanvas.width = tintCanvas.width = image.naturalWidth;
        editor.height = maskCanvas.height = proposalCanvas.height = hotspotCanvas.height = tintCanvas.height = image.naturalHeight;
        initializeMask();
        renderEditor();
        byId("canvas-empty").classList.add("hidden");
        byId("file-title").textContent = file.name;
        byId("file-meta").textContent = `${image.naturalWidth} × ${image.naturalHeight} px · ${(file.size / 1024 / 1024).toFixed(2)} MiB`;
        latestInspection = null;
        latestNarrative = null;
        latestResult = null;
        latestPlan = null;
        latestComparison = null;
        maskDirty = false;
        byId("result").classList.add("hidden");
        byId("placeholder").classList.remove("hidden");
        byId("inspection-section").classList.remove("hidden");
        byId("inspection-result").classList.add("hidden");
        byId("inspection-loading").classList.remove("hidden");
        setTool("brush");
        updateControls();
        setPipeline("detect");
        setStatus(t("ready"));
        const tasks = await Promise.allSettled([
          runAutomaticInspection(file, generation),
          generateProposalAndDraft(file, generation)
        ]);
        if (generation !== sourceGeneration) return;
        const inspectionSucceeded = tasks[0].status === "fulfilled" && tasks[0].value === true;
        const draftSucceeded = tasks[1].status === "fulfilled" && tasks[1].value === true;
        if (!inspectionSucceeded) {
          byId("inspection-loading").classList.remove("hidden");
          byId("inspection-loading-text").textContent = t("inspectionFailed");
        }
        setPipeline(draftSucceeded ? "review" : "draft");
        setStatus(inspectionSucceeded && draftSucceeded ? t("pipelineComplete") : t("pipelinePartial"), !inspectionSucceeded && !draftSucceeded);
      }

      function writeBinaryImage(image, canvas, context) {
        context.clearRect(0, 0, canvas.width, canvas.height);
        context.drawImage(image, 0, 0);
        const pixels = context.getImageData(0, 0, canvas.width, canvas.height);
        for (let index = 0; index < pixels.data.length; index += 4) {
          const alpha = pixels.data[index] >= 128 ? 255 : 0;
          pixels.data[index] = 255;
          pixels.data[index + 1] = 255;
          pixels.data[index + 2] = 255;
          pixels.data[index + 3] = alpha;
        }
        context.clearRect(0, 0, canvas.width, canvas.height);
        context.putImageData(pixels, 0, 0);
      }

      async function applyProposal(payload) {
        const proposalImage = new Image();
        proposalImage.src = payload.artifacts["proposal-mask.png"];
        const hotspotImage = new Image();
        const hotspotUrl = payload.artifacts["review-hotspots.png"];
        if (hotspotUrl) hotspotImage.src = hotspotUrl;
        await Promise.all([
          proposalImage.decode(),
          hotspotUrl ? hotspotImage.decode() : Promise.resolve()
        ]);
        if (proposalImage.naturalWidth !== maskCanvas.width || proposalImage.naturalHeight !== maskCanvas.height) {
          throw new Error("proposal mask dimensions do not match the source");
        }
        if (hotspotUrl && (hotspotImage.naturalWidth !== maskCanvas.width || hotspotImage.naturalHeight !== maskCanvas.height)) {
          throw new Error("review hotspot dimensions do not match the source");
        }
        writeBinaryImage(proposalImage, proposalCanvas, proposalContext);
        hotspotContext.clearRect(0, 0, hotspotCanvas.width, hotspotCanvas.height);
        if (hotspotUrl) writeBinaryImage(hotspotImage, hotspotCanvas, hotspotContext);
        activeProposalId = payload.proposal_id;
        proposalSuppressed = false;
        reviewHotspotsVisible = Boolean(hotspotUrl);
        latestProposal = payload;
        const guidance = payload.evidence && payload.evidence.review_guidance;
        const ranking = guidance && guidance.ranking;
        hotspotComponents = ranking && Array.isArray(ranking.ranked_hotspots) ? ranking.ranked_hotspots : [];
        reviewedHotspotIds = new Set();
        hotspotDecisions = new Map();
        hotspotDraftNotes = new Map();
        activeHotspotIndex = hotspotComponents.length ? 0 : -1;
        reviewProgressDirty = false;
        strokes = [];
        activeStroke = null;
        maskDirty = false;
        rebuildMask();
        renderEditor();
        renderProposalState();
        renderHotspotReview();
        updateControls();
      }

      async function generateProposal(file = sourceFile, generation = sourceGeneration) {
        if (!file) return false;
        byId("proposal-sensitivity").disabled = true;
        byId("proposal-state").textContent = t("proposalRunning");
        const form = new FormData();
        form.append("image", file, file.name);
        form.append("sensitivity", byId("proposal-sensitivity").value);
        try {
          const response = await fetch("/api/metrology/proposals", { method: "POST", body: form });
          const payload = await response.json();
          if (!response.ok) throw payload.error || payload;
          if (generation !== sourceGeneration) return false;
          if (!payload.candidate_found) {
            byId("proposal-state").textContent = t("proposalEmpty");
            return false;
          }
          await applyProposal(payload);
          setTool("brush");
          return true;
        } catch (error) {
          const message = error && (language === "zh" ? error.message_zh : error.message_en);
          const recovery = error && (language === "zh" ? error.recovery_zh : error.recovery_en);
          byId("proposal-state").textContent = [message, recovery].filter(Boolean).join(" — ") || t("failed");
          throw error;
        } finally {
          updateControls();
        }
      }

      async function generateProposalAndDraft(file, generation) {
        const found = await generateProposal(file, generation);
        if (!found || generation !== sourceGeneration) return false;
        setPipeline("draft");
        setStatus(t("autoDrafting"));
        const drafted = await runMeasurement({ automatic: true, generation });
        if (drafted && generation === sourceGeneration) setPipeline("review");
        return drafted;
      }

      function pointerDown(event) {
        if (!sourceImage || measurementOperationCount > 0) return;
        event.preventDefault();
        const point = canvasPosition(event);
        hoverPoint = point;
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
        markMaskDirty();
        renderEditor();
        updateControls();
      }

      function pointerMove(event) {
        const point = canvasPosition(event);
        hoverPoint = point;
        if (!drawing || !activeStroke) {
          renderEditor();
          return;
        }
        event.preventDefault();
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
        renderEditor();
        updateControls();
      }

      function loupePointerDown(event) {
        if (!sourceImage || !hotspotLoupeViewport || measurementOperationCount > 0) return;
        if (tool === "point") {
          setStatus(t("loupeToolRequired"), true);
          return;
        }
        event.preventDefault();
        const point = loupeCanvasPosition(event);
        if (!point) return;
        const hotspot = hotspotComponents[activeHotspotIndex];
        if (!hotspot) return;
        hoverPoint = point;
        loupeDrawing = true;
        hotspotLoupe.setPointerCapture(event.pointerId);
        loupeActiveStroke = {
          tool,
          size: Number(byId("brush-size").value),
          points: [point],
          input_surface: "synchronized_hotspot_loupe",
          hotspot_id: hotspot.hotspot_id,
          previous_hotspot_reviewed: reviewedHotspotIds.has(hotspot.hotspot_id),
          previous_hotspot_decision: hotspotDecisions.has(hotspot.hotspot_id)
            ? { ...hotspotDecisions.get(hotspot.hotspot_id) }
            : null
        };
        strokes.push(loupeActiveStroke);
        drawStroke(maskContext, loupeActiveStroke);
        recordHotspotDecision(
          tool === "eraser" ? "false_positive_removed" : "missed_crack_added"
        );
        markMaskDirty();
        renderEditor();
        updateControls();
      }

      function loupePointerMove(event) {
        const point = loupeCanvasPosition(event);
        if (!point) return;
        hoverPoint = point;
        if (!loupeDrawing || !loupeActiveStroke) {
          renderEditor();
          return;
        }
        event.preventDefault();
        const previous = loupeActiveStroke.points[loupeActiveStroke.points.length - 1];
        if (Math.hypot(point.x - previous.x, point.y - previous.y) < .35) return;
        loupeActiveStroke.points.push(point);
        drawStroke(maskContext, { ...loupeActiveStroke, points: [previous, point] });
        renderEditor();
      }

      function loupePointerUp(event) {
        if (!loupeDrawing) return;
        loupeDrawing = false;
        loupeActiveStroke = null;
        try { hotspotLoupe.releasePointerCapture(event.pointerId); } catch {}
        renderEditor();
        updateControls();
      }

      function maskBlob() {
        return new Promise((resolve, reject) => maskCanvas.toBlob((blob) => blob ? resolve(blob) : reject(new Error("mask export failed")), "image/png"));
      }

      function formNumber(id) {
        return String(Number(byId(id).value));
      }

      async function runMeasurement({ automatic = false, generation = sourceGeneration } = {}) {
        if (!sourceFile || (!activeProposalId && strokes.length === 0)) {
          setStatus(t("drawingRequired"), true);
          return false;
        }
        const mode = automatic ? "pixel" : byId("calibration-mode").value;
        if (mode === "manual" && calibrationPoints.length !== 4) {
          setStatus(t("pointsRequired"), true);
          return false;
        }
        measurementOperationCount += 1;
        updateControls();
        setStatus(automatic ? t("autoDrafting") : t("measuring"));
        try {
          const mask = await maskBlob();
          if (generation !== sourceGeneration) return false;
          const form = new FormData();
          form.append("image", sourceFile, sourceFile.name);
          form.append("mask", mask, "browser-mask.png");
          form.append("calibration_mode", mode);
          form.append("uncertainty_samples", automatic ? "0" : formNumber("uncertainty-samples"));
          form.append("segmentation_radius_pixels", formNumber("boundary-radius"));
          form.append("review_state", automatic ? "automatic_draft" : "human_reviewed");
          if (activeProposalId) form.append("proposal_id", activeProposalId);
          if (!automatic && activeProposalId) {
            form.append("reviewed_hotspots", JSON.stringify(Array.from(reviewedHotspotIds)));
            const decisions = hotspotComponents
              .map((hotspot) => hotspotDecisions.get(hotspot.hotspot_id))
              .filter(Boolean);
            form.append("hotspot_decisions", JSON.stringify(decisions));
          }
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
          if (generation !== sourceGeneration) return false;
          if (!automatic) {
            maskDirty = false;
            reviewProgressDirty = false;
          }
          renderResult(payload);
          setStatus(automatic ? t("autoDraftComplete") : t("complete"));
          if (!automatic) {
            setPipeline("saved");
            byId("result").scrollIntoView({ behavior: "smooth", block: "start" });
          }
          return true;
        } catch (error) {
          const message = error && (language === "zh" ? error.message_zh : error.message_en);
          const recovery = error && (language === "zh" ? error.recovery_zh : error.recovery_en);
          setStatus([message, recovery].filter(Boolean).join(" — ") || (automatic ? t("autoDraftFailed") : t("failed")), true);
          return false;
        } finally {
          measurementOperationCount = Math.max(0, measurementOperationCount - 1);
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
        const newRun = !latestResult || latestResult.run_id !== payload.run_id;
        latestResult = payload;
        if (newRun) {
          latestPlan = null;
          latestComparison = null;
          byId("plan-result").classList.add("hidden");
          byId("comparison-result").classList.add("hidden");
          byId("comparison-map").classList.add("hidden");
          byId("change-map-image").removeAttribute("src");
        }
        const measurement = payload.measurement;
        const physical = measurement.physical_geometry;
        const geometry = physical || measurement.pixel_geometry;
        const unit = geometry.unit === "pixel" ? "px" : geometry.unit;
        const topology = measurement.topology;
        const widths = geometry.width_distribution;
        const inputEvidence = measurement.run && measurement.run.input_evidence;
        const reviewState = inputEvidence && inputEvidence.review_state ? inputEvidence.review_state : "human_reviewed";
        byId("placeholder").classList.add("hidden");
        byId("result").classList.remove("hidden");
        byId("run-id").textContent = payload.run_id;
        byId("mode-badge").textContent = reviewState === "automatic_draft" ? t("draftBadge") : (physical ? t("physical") : t("pixel"));
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
        const maskEvidence = inputEvidence && inputEvidence.mask;
        const revision = maskEvidence && maskEvidence.proposal_revision;
        const feedbackUrl = payload.artifacts["active-learning-feedback.zip"];
        byId("feedback-panel").classList.toggle("hidden", !feedbackUrl);
        if (feedbackUrl) byId("feedback-download").href = feedbackUrl;
        else byId("feedback-download").removeAttribute("href");
        if (revision) {
          addEvidence(t("humanAdded"), revision.human_added_pixels);
          addEvidence(t("humanRemoved"), revision.human_removed_pixels);
          addEvidence(t("proposalIou"), number(revision.proposal_final_iou, 4));
          addEvidence(t("changedRatio"), `${(Number(revision.changed_image_ratio) * 100).toFixed(4)}%`);
          const hotspotReview = revision.hotspot_review;
          if (hotspotReview && hotspotReview.ranked_hotspot_count) {
            addEvidence(t("inspectedHotspots"), `${hotspotReview.reviewed_hotspot_count}/${hotspotReview.ranked_hotspot_count}`);
            addEvidence(t("priorityCoverage"), `${(Number(hotspotReview.ranked_priority_coverage_ratio || 0) * 100).toFixed(1)}%`);
            addEvidence(t("decidedHotspots"), `${hotspotReview.decided_hotspot_count}/${hotspotReview.ranked_hotspot_count}`);
            addEvidence(t("decisionCoverage"), `${(Number(hotspotReview.ranked_decision_priority_coverage_ratio || 0) * 100).toFixed(1)}%`);
            if (feedbackUrl) addEvidence(t("feedbackItems"), hotspotReview.decided_hotspot_count);
          }
        }
        const calibration = measurement.run && measurement.run.input_evidence && measurement.run.input_evidence.calibration;
        const field = calibration && calibration.field_detection;
        if (field) {
          addEvidence(t("aruco"), `${Number(field.minimum_marker_perimeter_pixels).toFixed(1)} px`);
          addEvidence(t("quad"), `${(Number(field.calibration_quadrilateral_image_ratio) * 100).toFixed(1)}%`);
        }
        byId("plan-button").disabled = !physical;
        byId("plan-note").textContent = physical ? t("planReady") : t("planPixel");
        updateReviewUI();
        loadRunHistory();
      }

      function inputNumber(id) {
        const value = byId(id).value.trim();
        return value === "" ? null : Number(value);
      }

      function signedPercent(value) {
        if (value === null || value === undefined) return "—";
        const number = Number(value);
        return `${number >= 0 ? "+" : ""}${number.toFixed(2)}%`;
      }

      function renderUtilityResult(element, title, lines, url, alert = false) {
        element.replaceChildren();
        element.classList.remove("hidden");
        element.classList.toggle("alert", alert);
        const heading = document.createElement("strong");
        heading.textContent = title;
        element.appendChild(heading);
        lines.forEach((line) => {
          const row = document.createElement("div");
          row.textContent = line;
          element.appendChild(row);
        });
        if (url) {
          const link = document.createElement("a");
          link.className = "download-link";
          link.href = url;
          link.download = "";
          link.textContent = t("downloadJson");
          element.appendChild(link);
        }
      }

      async function createPlan() {
        if (!latestResult || !latestResult.measurement.physical_geometry) return;
        byId("plan-button").disabled = true;
        setStatus(t("planRunning"));
        const form = new FormData();
        form.append("route_width_mm", String(inputNumber("route-width")));
        form.append("route_depth_mm", String(inputNumber("route-depth")));
        form.append("waste_percent", String(inputNumber("waste-percent")));
        const cost = inputNumber("unit-cost");
        if (cost !== null) form.append("unit_cost_per_liter", String(cost));
        try {
          const runId = encodeURIComponent(latestResult.run_id);
          const response = await fetch(`/api/metrology/runs/${runId}/maintenance-plan`, { method: "POST", body: form });
          const payload = await response.json();
          if (!response.ok) throw payload.error || payload;
          latestPlan = payload;
          renderPlan(payload);
          setStatus(t("planComplete"));
        } catch (error) {
          const message = error && (language === "zh" ? error.message_zh : error.message_en);
          setStatus(message || t("failed"), true);
        } finally {
          byId("plan-button").disabled = !latestResult.measurement.physical_geometry;
        }
      }

      function renderPlan(payload) {
        const quantities = payload.plan.quantities;
        const lines = [
          `${t("treatmentLength")}: ${Number(quantities.treatment_length_m).toFixed(3)} m`,
          `${t("procurementVolume")}: ${Number(quantities.procurement_volume_liters).toFixed(3)} L`
        ];
        if (quantities.estimated_material_cost !== null) {
          lines.push(`${t("estimatedCost")}: ${Number(quantities.estimated_material_cost).toFixed(2)}`);
        }
        renderUtilityResult(byId("plan-result"), t("planComplete"), lines, payload.plan_url);
      }

      async function loadRunHistory() {
        const select = byId("baseline-run");
        select.replaceChildren();
        const empty = document.createElement("option");
        empty.value = "";
        empty.textContent = "—";
        select.appendChild(empty);
        byId("compare-button").disabled = true;
        if (!latestResult || !latestResult.measurement.physical_geometry) return;
        try {
          const response = await fetch("/api/metrology/runs?limit=100");
          const payload = await response.json();
          if (!response.ok) throw payload.error || payload;
          payload.items.filter((item) => item.run_id !== latestResult.run_id).forEach((item) => {
            const option = document.createElement("option");
            option.value = item.run_id;
            const date = item.created_at_utc ? new Date(item.created_at_utc).toLocaleDateString(language === "zh" ? "zh-CN" : "en") : "—";
            const source = item.source_filename || item.run_id;
            option.textContent = `${date} · ${source} · ${Number(item.network_length).toFixed(3)} ${item.unit}`;
            select.appendChild(option);
          });
          if (select.options.length > 1) {
            select.selectedIndex = 1;
            byId("compare-button").disabled = false;
          } else {
            byId("comparison-result").classList.remove("hidden");
            byId("comparison-result").textContent = t("noBaseline");
          }
        } catch {
          byId("comparison-result").classList.remove("hidden");
          byId("comparison-result").textContent = t("noBaseline");
        }
      }

      async function compareGrowth() {
        if (!latestResult || !byId("baseline-run").value) return;
        byId("compare-button").disabled = true;
        setStatus(t("compareRunning"));
        const form = new FormData();
        form.append("baseline_run_id", byId("baseline-run").value);
        form.append("current_run_id", latestResult.run_id);
        form.append("elapsed_days", String(inputNumber("elapsed-days")));
        form.append("length_review_threshold_percent", String(inputNumber("length-threshold")));
        form.append("width_review_threshold_percent", String(inputNumber("width-threshold")));
        form.append("match_tolerance_mm", String(inputNumber("match-tolerance")));
        try {
          const response = await fetch("/api/metrology/compare", { method: "POST", body: form });
          const payload = await response.json();
          if (!response.ok) throw payload.error || payload;
          latestComparison = payload;
          renderComparison(payload);
          setStatus(t("compareComplete"));
        } catch (error) {
          const message = error && (language === "zh" ? error.message_zh : error.message_en);
          setStatus(message || t("failed"), true);
        } finally {
          byId("compare-button").disabled = !byId("baseline-run").value;
        }
      }

      function renderComparison(payload) {
        const comparison = payload.comparison;
        const changes = comparison.changes;
        const spatial = comparison.spatial_change;
        const review = comparison.review_rule.human_review_required;
        const lines = [
          `${t("lengthChange")}: ${signedPercent(changes.network_length_m.percent)}`,
          `${t("widthChange")}: ${signedPercent(changes.p95_width_mm.percent)}`,
          `${t("dailyGrowth")}: ${Number(changes.network_length_growth_m_per_day).toFixed(6)} m/day`
        ];
        if (spatial) {
          const quality = spatial.alignment_quality.status === "strong" ? t("strongAlignment") : t("acceptableAlignment");
          lines.push(`${t("alignmentQuality")}: ${quality} · ${Number(spatial.alignment_quality.frame_dimension_mismatch_percent).toFixed(2)}%`);
          lines.push(`${t("addedArea")}: ${Number(spatial.classification.suspected_added_area_cm2).toFixed(2)} cm²`);
          lines.push(`${t("missingArea")}: ${Number(spatial.classification.suspected_missing_area_cm2).toFixed(2)} cm²`);
        }
        renderUtilityResult(
          byId("comparison-result"),
          review ? t("reviewRequired") : t("withinThreshold"),
          lines,
          payload.comparison_url,
          review
        );
        const changeMapUrl = payload.artifacts && payload.artifacts["change-map.png"];
        byId("comparison-map").classList.toggle("hidden", !changeMapUrl);
        if (changeMapUrl) byId("change-map-image").src = changeMapUrl;
      }

      editor.addEventListener("pointerdown", pointerDown);
      editor.addEventListener("pointermove", pointerMove);
      editor.addEventListener("pointerup", pointerUp);
      editor.addEventListener("pointercancel", pointerUp);
      editor.addEventListener("pointerleave", () => {
        if (!drawing) {
          hoverPoint = null;
          renderEditor();
        }
      });
      hotspotLoupe.addEventListener("pointerdown", loupePointerDown);
      hotspotLoupe.addEventListener("pointermove", loupePointerMove);
      hotspotLoupe.addEventListener("pointerup", loupePointerUp);
      hotspotLoupe.addEventListener("pointercancel", loupePointerUp);
      hotspotLoupe.addEventListener("pointerleave", () => {
        if (!loupeDrawing) {
          hoverPoint = null;
          renderEditor();
        }
      });
      byId("source-input").addEventListener("change", (event) => loadSource(event.target.files[0]));
      byId("replace-button").addEventListener("click", () => byId("source-input").click());
      byId("proposal-sensitivity").addEventListener("input", () => {
        byId("proposal-sensitivity-value").textContent = String(Math.round(Number(byId("proposal-sensitivity").value) * 100));
      });
      byId("proposal-sensitivity").addEventListener("change", async () => {
        if (!sourceFile) return;
        setStatus(t("proposalRunning"));
        try {
          const drafted = await generateProposalAndDraft(sourceFile, sourceGeneration);
          setPipeline(drafted ? "review" : "draft");
          setStatus(drafted ? t("autoDraftComplete") : t("proposalEmpty"), !drafted);
        } catch {
          setStatus(t("pipelinePartial"), true);
        }
      });
      byId("brush-tool").addEventListener("click", () => setTool("brush"));
      byId("eraser-tool").addEventListener("click", () => setTool("eraser"));
      byId("point-tool").addEventListener("click", () => setTool("point"));
      byId("brush-size").addEventListener("input", () => {
        byId("brush-value").textContent = byId("brush-size").value;
        renderEditor();
      });
      byId("undo-button").addEventListener("click", () => {
        const removedStroke = strokes.pop();
        if (removedStroke && removedStroke.input_surface === "synchronized_hotspot_loupe" && removedStroke.hotspot_id) {
          if (removedStroke.previous_hotspot_decision) {
            hotspotDecisions.set(
              removedStroke.hotspot_id,
              removedStroke.previous_hotspot_decision
            );
          } else {
            hotspotDecisions.delete(removedStroke.hotspot_id);
          }
          if (removedStroke.previous_hotspot_reviewed) {
            reviewedHotspotIds.add(removedStroke.hotspot_id);
          } else {
            reviewedHotspotIds.delete(removedStroke.hotspot_id);
          }
          reviewProgressDirty = true;
        }
        rebuildMask();
        maskDirty = strokes.length > 0;
        setPipeline("review");
        updateReviewUI();
        renderEditor();
        updateControls();
      });
      byId("clear-button").addEventListener("click", () => {
        maskContext.clearRect(0, 0, maskCanvas.width, maskCanvas.height);
        strokes = [];
        activeStroke = null;
        proposalSuppressed = Boolean(activeProposalId);
        markMaskDirty();
        renderEditor();
        updateControls();
      });
      byId("hotspot-toggle").addEventListener("click", () => {
        reviewHotspotsVisible = !reviewHotspotsVisible;
        updateHotspotToggle();
        renderEditor();
      });
      byId("hotspot-previous").addEventListener("click", () => {
        focusHotspot(activeHotspotIndex - 1);
      });
      byId("hotspot-next").addEventListener("click", () => {
        focusHotspot(activeHotspotIndex + 1);
      });
      byId("hotspot-reviewed").addEventListener("click", () => {
        const hotspot = hotspotComponents[activeHotspotIndex];
        if (!hotspot) return;
        if (reviewedHotspotIds.has(hotspot.hotspot_id)) {
          reviewedHotspotIds.delete(hotspot.hotspot_id);
          hotspotDecisions.delete(hotspot.hotspot_id);
        } else {
          reviewedHotspotIds.add(hotspot.hotspot_id);
        }
        reviewProgressDirty = true;
        setPipeline("review");
        renderHotspotReview();
        updateReviewUI();
      });
      document.querySelectorAll(".hotspot-decision-button").forEach((button) => {
        button.addEventListener("click", () => recordHotspotDecision(button.dataset.disposition));
      });
      byId("hotspot-note").addEventListener("input", (event) => {
        const hotspot = hotspotComponents[activeHotspotIndex];
        if (!hotspot) return;
        const note = event.target.value.slice(0, 160);
        hotspotDraftNotes.set(hotspot.hotspot_id, note);
        const decision = hotspotDecisions.get(hotspot.hotspot_id);
        if (decision) {
          hotspotDecisions.set(hotspot.hotspot_id, {
            hotspot_id: hotspot.hotspot_id,
            disposition: decision.disposition,
            ...(note.trim() ? { note: note.trim() } : {})
          });
          reviewProgressDirty = true;
          setPipeline("review");
          updateReviewUI();
        }
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
      byId("measure-button").addEventListener("click", () => runMeasurement());
      byId("demo-button").addEventListener("click", runDemo);
      byId("narrative-button").addEventListener("click", generateNarrative);
      byId("plan-button").addEventListener("click", createPlan);
      byId("compare-button").addEventListener("click", compareGrowth);
      byId("baseline-run").addEventListener("change", () => {
        byId("compare-button").disabled = !byId("baseline-run").value;
      });
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
