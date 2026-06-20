// ── DESIGN TOKENS ──────────────────────────────────────────────────────────────
export const T = {
  bg0:    "#07090F",
  bg1:    "#0C1018",
  bg2:    "#111520",
  bg3:    "#171C2D",
  bg4:    "#1C2238",
  border: "#1E2640",
  border2:"#232B42",
  text0:  "#EEF1FA",
  text1:  "#B8C0D8",
  text2:  "#6B7699",
  text3:  "#3D4663",
  amber:  "#F5A623",
  amberD: "#C4841A",
  amberL: "#FFC554",
  green:  "#22D47A",
  greenD: "#15944F",
  red:    "#FF4F5E",
  redD:   "#C43040",
  blue:   "#4D8FFF",
  blueD:  "#2B5FCC",
  purple: "#A855F7",
  teal:   "#2DD4BF",
  mono:   "'JetBrains Mono', monospace",
  sans:   "'Space Grotesk', system-ui, sans-serif",
}

export const MARKETPLACE_LABELS: Record<string, string> = {
  amazon_us: "US", amazon_de: "Germany", amazon_uk: "UK", amazon_fr: "France",
  amazon_it: "Italy", amazon_es: "Spain", amazon_ca: "Canada", amazon_jp: "Japan",
}
export const marketplaceLabel = (mp: string) => MARKETPLACE_LABELS[mp] ?? mp.replace("amazon_", "").toUpperCase()

export const css = `
  *{box-sizing:border-box;margin:0;padding:0}
  :root{font-family:${T.sans};background:${T.bg0};color:${T.text0};-webkit-font-smoothing:antialiased}
  ::-webkit-scrollbar{width:4px;height:4px}
  ::-webkit-scrollbar-track{background:${T.bg1}}
  ::-webkit-scrollbar-thumb{background:${T.border2};border-radius:2px}
  .mono{font-family:${T.mono}}
  @keyframes pulse{0%,100%{opacity:1}50%{opacity:.4}}
  @keyframes fadeIn{from{opacity:0;transform:translateY(6px)}to{opacity:1;transform:translateY(0)}}
  @keyframes slideIn{from{opacity:0;transform:translateX(-8px)}to{opacity:1;transform:translateX(0)}}
  @keyframes spin{to{transform:rotate(360deg)}}
  .anim-fade{animation:fadeIn .3s ease both}
  .anim-slide{animation:slideIn .2s ease both}
  .row-hover:hover{background:${T.bg3}!important;cursor:pointer}
  .btn-ghost{border:none;background:transparent;color:${T.text1};cursor:pointer;border-radius:6px;display:inline-flex;align-items:center;gap:6px;font-size:13px;font-family:${T.sans};padding:6px 10px;transition:all .15s}
  .btn-ghost:hover{background:${T.bg4};color:${T.text0}}
  .btn-primary{border:none;background:${T.amber};color:#000;cursor:pointer;border-radius:7px;display:inline-flex;align-items:center;gap:6px;font-size:13px;font-weight:600;font-family:${T.sans};padding:7px 14px;transition:all .15s}
  .btn-primary:hover{background:${T.amberL}}
  .badge{display:inline-flex;align-items:center;gap:4px;font-size:10px;font-weight:600;padding:2px 7px;border-radius:4px;letter-spacing:.04em;font-family:${T.mono};white-space:nowrap}
  .input{background:${T.bg3};border:1px solid ${T.border};color:${T.text0};border-radius:7px;padding:7px 12px;font-size:13px;font-family:${T.sans};outline:none;width:100%;transition:border-color .15s}
  .input:focus{border-color:${T.blue}}
  .input::placeholder{color:${T.text3}}
  .card{background:${T.bg2};border:1px solid ${T.border};border-radius:10px;padding:16px}
  .card-soft{background:${T.bg2};border-radius:10px;padding:16px;box-shadow:0 1px 4px rgba(0,0,0,.25)}
  .divider{height:1px;background:${T.border};margin:12px 0}
  .tag-new{background:#0F2A1A;color:${T.green};border:1px solid ${T.greenD}}
  .tag-ret{background:#1A2010;color:#90EE90;border:1px solid #3A5A2A}
  .tag-exit{background:#2A100F;color:${T.red};border:1px solid ${T.redD}}
  .tag-top10{background:#1A1500;color:${T.amber};border:1px solid ${T.amberD}}
  .tag-price{background:#0D1A30;color:${T.blue};border:1px solid ${T.blueD}}
  .tag-stock{background:#200D25;color:${T.purple};border:1px solid #5A2580}
  .tag-listing{background:#0A1A1A;color:${T.teal};border:1px solid #1A4040}
  .tag-info{background:${T.bg3};color:${T.text1};border:1px solid ${T.border}}
  .dot-live{width:6px;height:6px;border-radius:50%;background:${T.green};animation:pulse 2s infinite}
  .dot-warn{width:6px;height:6px;border-radius:50%;background:${T.amber};animation:pulse 2s infinite}
  .dot-dead{width:6px;height:6px;border-radius:50%;background:${T.text3}}
`
