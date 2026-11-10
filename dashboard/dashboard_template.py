"""HTML + vanilla-JS template for the Dual-Duty Tax dashboard.

The marker /*__DATA__*/ is replaced with the embedded JSON payload by
build_dashboard.py. No external network resources, no scripts loaded from a
CDN: the file is fully self-contained and works offline.
"""

HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Dual-Duty Tax \u2014 Coach Dashboard</title>
<style>
  :root{
    --bg:#f6f7f8; --panel:#ffffff; --ink:#1c2733; --muted:#64727f;
    --line:#dfe4e8; --accent:#1f4e79; --accent2:#7030a0;
    --good:#2e7d57; --bad:#b0472b; --chip:#eef2f6;
  }
  *{box-sizing:border-box}
  body{margin:0;font:14px/1.5 -apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;
       background:var(--bg);color:var(--ink)}
  header{background:var(--panel);border-bottom:1px solid var(--line);padding:16px 22px}
  h1{margin:0;font-size:20px}
  .sub{color:var(--muted);font-size:13px;margin-top:3px}
  .wrap{max-width:1140px;margin:0 auto;padding:18px 22px 60px}
  .bar{display:flex;flex-wrap:wrap;gap:14px;align-items:center;justify-content:space-between;
       background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:12px 14px;margin:14px 0}
  .tabs{display:flex;gap:6px;flex-wrap:wrap}
  .tab{border:1px solid var(--line);background:#fff;border-radius:8px;padding:7px 12px;cursor:pointer;color:var(--ink)}
  .tab.active{background:var(--accent);color:#fff;border-color:var(--accent)}
  .toggle{display:flex;align-items:center;gap:8px}
  .seg{display:inline-flex;border:1px solid var(--line);border-radius:8px;overflow:hidden}
  .seg button{border:0;background:#fff;padding:7px 12px;cursor:pointer;color:var(--ink);font-weight:600}
  .seg button.on{background:var(--accent);color:#fff}
  .seg button:disabled{color:#aab3bb;cursor:not-allowed;background:#f1f3f5}
  .panel{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:16px 18px;margin:14px 0}
  .panel h2{margin:0 0 4px;font-size:16px}
  .panel .note{color:var(--muted);font-size:12.5px;margin:2px 0 12px}
  .cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:12px}
  .card{border:1px solid var(--line);border-radius:9px;padding:13px}
  .card .q{color:var(--muted);font-size:12.5px;margin-bottom:8px}
  .big{font-size:24px;font-weight:700}
  .unit{color:var(--muted);font-weight:500;font-size:13px}
  .ci{color:var(--muted);font-size:12.5px;margin-top:3px}
  .pill{display:inline-block;font-size:11px;padding:1px 7px;border-radius:20px;background:var(--chip);
        color:var(--muted);margin-left:6px}
  table{border-collapse:collapse;width:100%;font-size:13px}
  th,td{padding:7px 9px;border-bottom:1px solid var(--line);text-align:right;white-space:nowrap}
  th:first-child,td:first-child{text-align:left}
  th{cursor:pointer;user-select:none;position:sticky;top:0;background:#fbfcfd}
  th.sorted::after{content:" \u25be";color:var(--muted)}
  th.asc.sorted::after{content:" \u25b4"}
  tr:hover td{background:#fafcfe}
  .score{font-weight:700}
  .mutecell{color:var(--muted)}
  .filters{display:flex;gap:10px;flex-wrap:wrap;align-items:center;margin-bottom:12px}
  select,label{font-size:13px}
  select{padding:5px 7px;border:1px solid var(--line);border-radius:7px;background:#fff}
  .tag{font-size:11px;padding:1px 7px;border-radius:20px;border:1px solid var(--line);color:var(--muted)}
  .tag.good{color:var(--good);border-color:#bfe0cf}
  .tag.bad{color:var(--bad);border-color:#e8c6ba}
  .cohort{font-size:12.5px;color:var(--muted);margin:4px 0 10px}
  .hint{cursor:help;border-bottom:1px dotted var(--muted)}
  details{margin-top:10px}
  summary{cursor:pointer;color:var(--accent);font-weight:600}
  .prov{font-size:12px;color:var(--muted);line-height:1.8}
  .warn{background:#fff6ed;border:1px solid #f0d8bf;border-radius:8px;padding:8px 11px;color:#6b4a24;font-size:12.5px}
  .usebar{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin:4px 0 14px}
  .usecard{border:1px solid var(--line);border-left:3px solid var(--accent);border-radius:8px;
           padding:10px 12px;background:#fbfcfd;font-size:12.5px;color:var(--ink)}
  .usecard b{color:var(--accent)}
  @media(max-width:720px){.usebar{grid-template-columns:1fr}}
  .headline{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:12px;margin-top:8px}
  .hcard{border:1px solid var(--line);border-top:3px solid var(--accent);border-radius:9px;padding:13px;background:#fbfcfd}
  .hval{font-size:20px;font-weight:800;color:var(--accent);line-height:1.2}
  .hlabel{font-weight:700;margin-top:6px}
  .hsub{font-size:12px;color:var(--muted);margin-top:4px}
  .readme-link{color:var(--accent);text-decoration:none;font-size:13px;font-weight:600}
  .readme-link:hover{text-decoration:underline}
  .readline{font-size:13px;color:var(--ink);background:#eef2f6;border-radius:8px;padding:9px 12px;margin:2px 0 12px}
  .mlegend{display:grid;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));gap:10px;margin-bottom:14px}
  .mcard{border:1px solid var(--line);border-radius:8px;padding:9px 11px;background:#fff}
  .mname{font-weight:700;font-size:13px}
  .arrow{font-weight:600;font-size:11px;color:var(--good);background:#eaf5ef;border-radius:20px;padding:1px 7px;margin-left:4px;white-space:nowrap}
  .mplain{font-size:12.5px;color:var(--ink);margin:4px 0}
  .mrate{font-size:11.5px;color:var(--muted)}
  .mini{display:grid;grid-template-columns:1fr 1fr;gap:12px}
  .kv{display:flex;justify-content:space-between;border-bottom:1px dashed var(--line);padding:3px 0}
  .kv span:last-child{font-variant-numeric:tabular-nums}
  @media(max-width:720px){.mini{grid-template-columns:1fr}}
</style>
</head>
<body>
<header>
  <h1>The Dual-Duty Tax \u2014 Coach Dashboard</h1>
  <div class="sub">Who handles double duty \u2014 chip a rusher or leak out, then still make a play \u2014 and how well, compared to his own normal routes. Built for coaches &amp; scouts; numbers describe what was observed on tape, not a prediction.</div>
</header>
<div class="wrap">
  <div class="bar">
    <div class="tabs" id="tabs"></div>
    <div class="toggle">
      <span class="unit">View</span>
      <div class="seg" id="modeseg">
        <button id="m-actual" class="on" data-mode="actual">Actual values</button>
        <button id="m-score" data-mode="score">Relative score (1\u2013100)</button>
      </div>
    </div>
  </div>

  <div id="view"></div>

  <div class="panel">
    <details>
      <summary>Methodology &amp; sources</summary>
      <p class="note" style="margin-top:10px">
        <b>Relative score (1\u2013100).</b> Within a frozen peer cohort (same position group &amp; metric for players; same exact
        rusher count &amp; treatment definition for teams), each metric is oriented so larger is more favorable, tied values
        receive ascending <i>average</i> ranks, and the score is <code>1 + 99 \u00d7 (rank \u2212 1)/(N \u2212 1)</code> where N is the cohort
        size. Rounding is for display only. The cohort is frozen before any row is selected, so picking a row never changes its
        score. Scores are suppressed for sparse rows, missing comparisons, or cohorts with fewer than 10 eligible entities; if
        every value ties, the metric shows \u201cNo differentiation.\u201d Aggregate results with no peer distribution (Overview,
        Stay-or-Go) are never scored and stay in actual units even in score mode.
      </p>
      <p class="note">
        <b>Favorability.</b> Lower chip release delay is more favorable; greater depth retention and greater separation gain are
        more favorable; a more negative chip-minus-no-chip pressure difference is more favorable.
      </p>
      <p class="note">
        <b>Confidence intervals</b> stay in their original units from the source bootstrap; there are no score CIs. Actual values,
        units, sample counts, CIs, and missingness remain available via columns and hover tooltips in every mode.
      </p>
      <p class="note"><b>Interpretation guardrails.</b> Within-rusher and play-level pressure answer different questions
        (one rusher's own rate vs. the whole play). Timing-window retention (share of actual throws inside 2\u20135 s) differs from
        timing-data availability (share of plays with any timing record). Known no-throw exclusions (sack/run) differ from
        route features missing from the parquet. Receiving separation on go plays is observed separation when backs release \u2014
        not the counterfactual receiving cost of staying. Team comparisons are observational and often rest on very few games.
        Larger separation alone does not establish greater receiving value.</p>
      <div class="prov" id="prov"></div>
    </details>
  </div>
</div>

<script>
const DATA = /*__DATA__*/;
let MODE = "actual";
let TAB = "overview";

const fmt = (x, d=2) => (x===null||x===undefined) ? "\u2014" : (typeof x==="number" ? x.toFixed(d) : x);
const signed = (x, d=2) => (x===null||x===undefined) ? "\u2014" : (x>0?"+":"") + x.toFixed(d);
const el = (t, cls, html) => { const e=document.createElement(t); if(cls)e.className=cls; if(html!==undefined)e.innerHTML=html; return e; };

/* ---- tabs ---- */
const TABS = [
  ["overview","Overview"],
  ["players","Players \u2014 Dual-Duty Fit"],
  ["stayorgo","Stay or Go context"],
];
function renderTabs(){
  const box = document.getElementById("tabs"); box.innerHTML="";
  TABS.forEach(([k,label])=>{
    const b = el("button","tab"+(k===TAB?" active":""),label);
    b.onclick = ()=>{TAB=k; renderTabs(); render();};
    box.appendChild(b);
  });
}

/* ---- mode toggle ---- */
function setupMode(){
  const a=document.getElementById("m-actual"), s=document.getElementById("m-score");
  a.onclick=()=>{MODE="actual"; a.classList.add("on"); s.classList.remove("on"); render();};
  s.onclick=()=>{if(s.disabled)return; MODE="score"; s.classList.add("on"); a.classList.remove("on"); render();};
}

/* ---- score cell helper ---- */
function scoreCell(score, actualHtml, tip){
  if(MODE==="score"){
    if(score===null||score===undefined) return `<td class="mutecell" title="${tip||''}">n/a</td>`;
    return `<td class="score" title="${tip||''}">${score}</td>`;
  }
  return `<td title="${tip||''}">${actualHtml}</td>`;
}

/* ================= OVERVIEW ================= */
function viewOverview(){
  const o=DATA.overview, v=el("div");

  // quick-glance headline numbers
  const hp=el("div","panel");
  hp.appendChild(el("h2",null,"The Dual-Duty Tax at a glance"));
  hp.appendChild(el("div","note","The one-block summary: a chip hurts the rusher a lot and costs the receiver a little. Full detail in the tabs above."));
  const hg=el("div","headline");
  (o.headline||[]).forEach(h=>{
    const c=el("div","hcard");
    c.innerHTML=`<div class="hval">${h.value}</div><div class="hlabel">${h.label}</div><div class="hsub">${h.sub}</div>`;
    hg.appendChild(c);
  });
  hp.appendChild(hg);
  v.appendChild(hp);

  // what teams get out of this
  const gp=el("div","panel");
  gp.appendChild(el("h2",null,"What your team gets from this"));
  gp.appendChild(el("div","note","One question, three practical uses: when you ask a TE or back to chip, you trade a little of his route for a lot less pressure \u2014 here is how to use that trade."));
  const gg=el("div","usebar");
  gg.innerHTML = `
    <div class="usecard"><b>Protect the QB.</b> A chip cuts the chipped rusher\u2019s pressure rate from <b>11.4% to 7.5%</b>.
      Use the Players tab to find the TEs and backs whose chip barely delays their route \u2014 you get the protection
      without stalling the play.</div>
    <div class="usecard"><b>Call the right protection.</b> Know the real cost before you dial it up: a chip costs a TE about
      <b>1.3 s</b> and <b>3.8 yd</b> of route (less for backs). Match the chip to down &amp; distance instead of guessing.</div>
    <div class="usecard"><b>Build the roster.</b> Scouts can profile dual-threat TEs and backs: who holds route depth and
      still separates after chipping, and who needs development. Rank any single skill 1\u2013100 within position on the Players tab.</div>`;
  gp.appendChild(gg);
  v.appendChild(gp);

  const p=el("div","panel");
  p.appendChild(el("h2",null,"Chip pressure comparisons"));
  p.appendChild(el("div","note","Aggregate estimates with no peer distribution \u2014 shown in actual units in both modes (not scored)."));
  const cards=el("div","cards");
  o.cards.forEach(c=>{
    const card=el("div","card");
    card.innerHTML = `<div><b>${c.title}</b></div>
      <div class="q">${c.question}</div>
      <div class="big">${signed(c.estimate)} <span class="unit">${c.unit}</span></div>
      <div class="ci">95% CI [${fmt(c.ci_low)}, ${fmt(c.ci_high)}] \u00b7 ${c.n_label}: ${c.n}</div>
      <div class="ci" style="margin-top:6px">${c.note}</div>
      <div class="ci" style="margin-top:6px"><span class="tag">src: ${c.source}</span></div>`;
    cards.appendChild(card);
  });
  p.appendChild(cards);
  if(MODE==="score"){ p.insertBefore(el("div","warn","Overview is an aggregate with no peer cohort, so it stays in actual units even in score mode."), cards); }
  v.appendChild(p);

  // timing accounting
  const t=DATA.overview.timing, tp=el("div","panel");
  tp.appendChild(el("h2",null,"Timing accounting \u2014 availability vs. window retention"));
  tp.appendChild(el("div","note","Timing-data availability (any timing record) is distinct from window retention (actual throws landing inside 2\u20135 s). Known no-throw (sack/run) is distinct from missing route features."));
  const mini=el("div","mini");
  [["Chip plays",t.chip],["No-chip plays",t.nochip]].forEach(([lab,a])=>{
    const d=el("div");
    d.innerHTML=`<div><b>${lab}</b> \u00b7 ${a.traditional} traditional dropbacks</div>
      <div class="kv"><span>Timing-data availability</span><span>${a.timing_availability_pct}%</span></div>
      <div class="kv"><span>Window retention (within actual throws)</span><span>${a.window_retention_pct}%</span></div>
      <div class="kv"><span>Missing timing record</span><span>${a.missing_timing}</span></div>
      <div class="kv"><span>Known no-throw (sack/run)</span><span>${a.known_no_throw}</span></div>
      <div class="kv"><span>Throw, outside 2\u20135 s</span><span>${a.throw_out_window}</span></div>
      <div class="kv"><span>Throw, inside 2\u20135 s (retained)</span><span>${a.throw_in_window}</span></div>`;
    mini.appendChild(d);
  });
  tp.appendChild(mini);
  v.appendChild(tp);
  return v;
}

/* ================= TEAMS ================= */
let teamSort={col:"team",asc:true};
let teamFilters={treatment:"TE chip vs no TE chip",n_rushers:"4",team:"ALL"};
function viewTeams(){
  const v=el("div"), p=el("div","panel");
  p.appendChild(el("h2",null,"Team comparisons \u2014 TE chip vs. no TE chip"));
  p.appendChild(el("div","note","Observational; strata are often supported by very few games. The no-qualifying-chip sensitivity is a separate treatment definition, selectable below. Filters use only the exact rusher count & treatment supported by the source tables."));

  const rows=DATA.teams.rows;
  const treatments=[...new Set(rows.map(r=>r.treatment))];
  const rc=DATA.teams.rusher_counts;

  const f=el("div","filters");
  f.appendChild(mkSelect("Treatment",treatments,teamFilters.treatment,x=>{teamFilters.treatment=x;renderInto(p,teamTable);}));
  f.appendChild(mkSelect("Exact rushers",rc.map(String),teamFilters.n_rushers,x=>{teamFilters.n_rushers=x;renderInto(p,teamTable);}));
  const teamOpts=["ALL",...DATA.teams.teams];
  f.appendChild(mkSelect("Team",teamOpts,teamFilters.team,x=>{teamFilters.team=x;renderInto(p,teamTable);}));
  p.appendChild(f);
  const holder=el("div"); holder.id="team-holder"; p.appendChild(holder);
  renderInto(p, teamTable);
  v.appendChild(p);
  return v;
}
function teamTable(p){
  const holder=p.querySelector("#team-holder"); holder.innerHTML="";
  const key=`${teamFilters.treatment}||${teamFilters.n_rushers}`;
  const meta=DATA.teams.cohort_meta[key]||{n_eligible:0,note:"no cohort"};
  let rows=DATA.teams.rows.filter(r=>r.treatment===teamFilters.treatment && String(r.n_rushers)===teamFilters.n_rushers);
  if(teamFilters.team!=="ALL") rows=rows.filter(r=>r.team===teamFilters.team);

  const cohort=el("div","cohort");
  const scoreable = MODE==="score";
  let cnote="";
  if(meta.note==="no_differentiation") cnote=" \u2014 <b>No differentiation</b> (all eligible values tie)";
  else if(meta.note) cnote=` \u2014 scores suppressed (${meta.note})`;
  cohort.innerHTML=`Reference cohort: <b>${meta.n_eligible}</b> eligible teams at exactly ${teamFilters.n_rushers} rushers, treatment \u201c${teamFilters.treatment}\u201d.${scoreable?cnote:""} Scores describe observed relative standing only.`;
  holder.appendChild(cohort);

  if(MODE==="score" && (meta.note || meta.n_eligible<10)){
    holder.appendChild(el("div","warn","This cohort is not scoreable (fewer than 10 eligible teams or no differentiation). Showing actual values."));
  }

  const cols=[
    ["team","Team",r=>r.team],
    ["diff_pp", MODE==="score"?"Score":"TE\u2212noTE (pp)", null],
    ["te_chip_n","TE-chip plays",r=>r.te_chip_n],
    ["contributing_games","Games",r=>r.contributing_games===null?"\u2014":r.contributing_games],
    ["ci","95% CI (pp)",r=>r.ci_low===null?"\u2014":`[${fmt(r.ci_low,1)}, ${fmt(r.ci_high,1)}]`],
    ["status","Eligible",r=>r.eligible?`<span class="tag good">yes</span>`:`<span class="tag bad">no</span>`],
  ];
  const showScore = MODE==="score" && !meta.note && meta.n_eligible>=10;
  const tbl=el("table"), thead=el("thead"), tr=el("tr");
  cols.forEach(([ck,label])=>{
    const th=el("th",null,label);
    if(ck===teamSort.col) th.className=(teamSort.asc?"asc ":"")+"sorted";
    th.onclick=()=>{teamSort.asc = teamSort.col===ck ? !teamSort.asc : true; teamSort.col=ck; teamTable(p);};
    tr.appendChild(th);
  });
  thead.appendChild(tr); tbl.appendChild(thead);
  const sortv=r=>{
    if(teamSort.col==="diff_pp") return showScore ? (r.score??-1) : (r.diff_pp??1e9);
    if(teamSort.col==="ci") return r.ci_low??1e9;
    if(teamSort.col==="status") return r.eligible?1:0;
    const c=cols.find(c=>c[0]===teamSort.col); return c&&c[2]?c[2](r):"";
  };
  rows.sort((a,b)=>{const x=sortv(a),y=sortv(b); if(x<y)return teamSort.asc?-1:1; if(x>y)return teamSort.asc?1:-1; return a.team<b.team?-1:1;});
  const tb=el("tbody");
  rows.forEach(r=>{
    const row=el("tr");
    const tip=`TE\u2212noTE ${signed(r.diff_pp,1)} pp \u00b7 TE-chip plays ${r.te_chip_n} \u00b7 games ${r.contributing_games===null?'n/a':r.contributing_games} \u00b7 ${r.few_games_flag?'few games':'ok'} \u00b7 CI ${r.ci_low===null?'n/a':'['+fmt(r.ci_low,1)+', '+fmt(r.ci_high,1)+']'}`;
    row.innerHTML = `<td title="${tip}">${r.team}</td>`;
    if(showScore){
      row.innerHTML += r.eligible && r.score!==null ? `<td class="score" title="${tip}">${r.score}</td>` : `<td class="mutecell" title="${tip}">n/a</td>`;
    } else {
      row.innerHTML += `<td title="${tip}">${signed(r.diff_pp,1)}</td>`;
    }
    row.innerHTML += `<td>${r.te_chip_n}</td>`;
    row.innerHTML += `<td>${r.contributing_games===null?"\u2014":r.contributing_games}</td>`;
    row.innerHTML += `<td class="mutecell">${r.ci_low===null?"\u2014":"["+fmt(r.ci_low,1)+", "+fmt(r.ci_high,1)+"]"}</td>`;
    row.innerHTML += `<td>${r.eligible?'<span class="tag good">yes</span>':'<span class="tag bad">no</span>'}</td>`;
    tb.appendChild(row);
  });
  tbl.appendChild(tb); holder.appendChild(tbl);
}

/* ================= PLAYERS ================= */
let playerPG="TE";
let playerSort={col:"chip_release_delay_s",asc:false};
function viewPlayers(){
  const v=el("div"), p=el("div","panel");
  p.appendChild(el("h2",null,"Players \u2014 Dual-Duty Fit (TE &amp; RB/FB)"));
  p.appendChild(el("div","note","How a player performs when asked to do double duty \u2014 chip a rusher (or leak out) and still get into the route \u2014 measured against his own clean-route baseline. TE and RB/FB are never pooled; each is ranked only within its own group."));
  const use=el("div","usebar");
  use.innerHTML = `
    <div class="usecard"><b>For coaches \u2014 scheme fit.</b> Flip to <b>Relative score (1\u2013100)</b> and sort a column to find
      who already does the job you need: a quick release off the chip (keeps timing), depth held after contact, or
      separation when he leaks out. Higher score = better among peers at that one job.</div>
    <div class="usecard"><b>For scouts \u2014 development.</b> Stay on <b>Actual values</b> to see the raw cost in seconds and yards.
      A big release delay or depth loss vs. his clean baseline is a coachable gap; a strong leak separation shows upside as
      a dual-duty weapon. Sample sizes (chip / leak / clean routes) are shown so you can weight confidence.</div>`;
  p.appendChild(use);
  const f=el("div","filters");
  f.appendChild(mkSelect("Position group",["TE","RB"],playerPG,x=>{playerPG=x; renderInto(p,playerTable);}));
  p.appendChild(f);
  const holder=el("div"); holder.id="player-holder"; p.appendChild(holder);
  renderInto(p, playerTable);
  v.appendChild(p);
  return v;
}
function playerTable(p){
  const holder=p.querySelector("#player-holder"); holder.innerHTML="";
  const g=DATA.players.groups[playerPG];
  const metrics=DATA.players.metrics.filter(m=>!(playerPG==="RB" && m.col==="leak_sep_gain_yd"));

  const grpName = playerPG==="TE" ? "tight ends" : "running backs & fullbacks";
  // plain "how to read" line + per-metric meaning
  const readLine=el("div","readline");
  readLine.innerHTML = MODE==="score"
    ? `Showing <b>${grpName}</b>. Each column is scored <b>1\u2013100 among ${playerPG}s only</b> \u2014 <b>100 = best</b> at that one skill, 50 = middle of the pack. Blank means not enough routes to rate fairly. Click a column to sort.`
    : `Showing <b>${grpName}</b>. Numbers are the real cost/benefit vs. the player's own normal routes (seconds or yards). Switch to <b>Relative score (1\u2013100)</b> to see who ranks best. Click a column to sort; hover any number for detail.`;
  holder.appendChild(readLine);

  // per-metric plain meaning cards
  const legend=el("div","mlegend");
  metrics.forEach(m=>{
    const mm=g.metric_meta[m.col]||{n_eligible:0};
    let rateTxt = `${mm.n_eligible} ${playerPG}s have enough routes to rank`;
    if(mm.note==="no_differentiation") rateTxt="all tie \u2014 no separation between players";
    else if(mm.note) rateTxt="not enough data to rank";
    const c=el("div","mcard");
    c.innerHTML=`<div class="mname">${m.label} <span class="arrow">${m.arrow}</span></div>
      <div class="mplain">${m.plain}</div>
      <div class="mrate">Unit: ${m.unit}. ${rateTxt}.</div>`;
    legend.appendChild(c);
  });
  holder.appendChild(legend);

  const cols=[["name","Player",r=>r.name],["position","Pos",r=>r.position],
              ["n_chip","Chip routes",r=>r.n_chip],["n_leak","Leak routes",r=>r.n_leak],["n_clean","Clean routes",r=>r.n_clean]];
  metrics.forEach(m=>cols.push([m.col,(MODE==="score"?"\u2b50 ":"")+m.label+(MODE==="score"?" (1\u2013100)":` (${m.unit})`),null]));

  const tbl=el("table"), thead=el("thead"), tr=el("tr");
  cols.forEach(([ck,label])=>{
    const th=el("th",null,label);
    if(ck===playerSort.col) th.className=(playerSort.asc?"asc ":"")+"sorted";
    th.onclick=()=>{playerSort.asc = playerSort.col===ck ? !playerSort.asc : false; playerSort.col=ck; playerTable(p);};
    tr.appendChild(th);
  });
  thead.appendChild(tr); tbl.appendChild(thead);

  const metricByCol=Object.fromEntries(DATA.players.metrics.map(m=>[m.col,m]));
  const sortv=r=>{
    if(metricByCol[playerSort.col]){
      return MODE==="score" ? (r[playerSort.col+"__score"]??-1) : (r[playerSort.col]??-1e9);
    }
    const c=cols.find(c=>c[0]===playerSort.col); return c&&c[2]?c[2](r):"";
  };
  const rows=g.players.slice();
  rows.sort((a,b)=>{const x=sortv(a),y=sortv(b); if(x<y)return playerSort.asc?-1:1; if(x>y)return playerSort.asc?1:-1; return a.name<b.name?-1:1;});

  const tb=el("tbody");
  rows.forEach(r=>{
    const row=el("tr");
    let html=`<td>${r.name}</td><td>${r.position}</td><td>${r.n_chip}</td><td>${r.n_leak}</td><td>${r.n_clean}</td>`;
    metrics.forEach(m=>{
      const val=r[m.col], sc=r[m.col+"__score"];
      const mm=g.metric_meta[m.col]||{};
      const tip=`${m.label} \u2014 ${m.plain}\nActual: ${val===null?'not enough routes':signed(val)+' '+m.unit} (${m.arrow}).\nExact definition: ${m.defn}`;
      if(MODE==="score"){
        if(mm.note){ html+=`<td class="mutecell" title="${tip}">${mm.note==='no_differentiation'?'n/d':'n/a'}</td>`; }
        else if(sc===null||sc===undefined){ html+=`<td class="mutecell" title="${tip}">n/a</td>`; }
        else { html+=`<td class="score" title="${tip}">${sc}</td>`; }
      } else {
        html+=`<td title="${tip}">${val===null?'<span class="mutecell">\u2014</span>':signed(val)}</td>`;
      }
    });
    row.innerHTML=html; tb.appendChild(row);
  });
  tbl.appendChild(tb); holder.appendChild(tbl);

  const defs=el("div","note"); defs.style.marginTop="12px";
  defs.innerHTML="<b>Reading the numbers.</b> Every number compares a player to <i>his own</i> normal (\u201cclean\u201d) routes, so it already accounts for who he is. "
    + "A blank cell means he didn\u2019t run enough chip/leak routes to judge fairly. Scores (1\u2013100) only compare players at the same position. "
    + "These describe what was observed on tape \u2014 not a guarantee of future results. Hover any value for the exact definition.";
  holder.appendChild(defs);
}

/* ================= STAY OR GO ================= */
function viewStayGo(){
  const sg=DATA.stayorgo, v=el("div");
  const p=el("div","panel");
  p.appendChild(el("h2",null,"Stay or Go \u2014 pressure"));
  p.appendChild(el("div","note","Any-rusher pressure: stay-only minus go-only. 4-rusher and 5+ populations kept separate. Aggregate estimates \u2014 not scored."));
  if(MODE==="score") p.appendChild(el("div","warn","Stay-or-Go estimates have no peer cohort, so they stay in actual units even in score mode."));
  const cards=el("div","cards");
  sg.pressure.forEach(c=>{
    const card=el("div","card");
    card.innerHTML=`<div><b>${c.population}</b></div><div class="q">${c.metric}</div>
      <div class="big">${signed(c.estimate)} <span class="unit">${c.unit}</span></div>
      <div class="ci">95% CI [${fmt(c.ci_low)}, ${fmt(c.ci_high)}]</div>
      <div class="ci" style="margin-top:6px"><span class="tag">src: ${c.source}</span></div>`;
    cards.appendChild(card);
  });
  p.appendChild(cards); v.appendChild(p);

  const rp=el("div","panel");
  rp.appendChild(el("h2",null,"Stay or Go \u2014 observed receiving separation (go plays)"));
  rp.appendChild(el("div","note","Observed separation when backs release on go plays \u2014 NOT the counterfactual receiving cost of staying. Larger separation alone does not establish greater receiving value. \u201cThrow-like only\u201d restricts to pass_forward endpoints."));
  const tbl=el("table"), thead=el("thead");
  thead.innerHTML="<tr><th>Population</th><th>Endpoint scope</th><th>Separation (yd)</th><th>95% CI (yd)</th><th>Measured / eligible routes</th><th>Share</th><th>Known no-throw</th><th>Parquet-absent</th></tr>";
  tbl.appendChild(thead);
  const tb=el("tbody");
  sg.receiving.forEach(r=>{
    const scope=r.throwlike_only?"throw-like only":"play-window end (all)";
    const pop=r.is_5plus?"5+ rushers":"4 rushers (baseline)";
    const covTip = r.true_throw_route_coverage==="unavailable_no_independent_endpoint_table"
      ? `true throw-route coverage unavailable; conservative lower bound ${fmt(r.conservative_lb,3)}` : "endpoint not restricted";
    const tr=el("tr");
    tr.innerHTML=`<td>${pop}</td><td title="${covTip}" class="hint">${scope}</td>
      <td>${fmt(r.estimate)}</td><td class="mutecell">[${fmt(r.ci_low)}, ${fmt(r.ci_high)}]</td>
      <td>${r.measured_routes} / ${r.eligible_routes}</td><td>${(r.share_of_eligible*100).toFixed(1)}%</td>
      <td title="ended in sack/run \u2014 not missing">${r.known_no_throw_routes}</td>
      <td title="route missing from parquet \u2014 endpoint unknown">${r.parquet_absent_routes}</td>`;
    tb.appendChild(tr);
  });
  tbl.appendChild(tb); rp.appendChild(tbl);
  if(sg.throwlike_on_sack_plays!==null){
    rp.appendChild(el("div","note",`Endpoint note: ${sg.throwlike_on_sack_records} throw-like route records on ${sg.throwlike_on_sack_plays} sack-labeled plays reflect a tracking-endpoint vs. plays.csv.passResult discrepancy (endpoint is shared across a play's routes), not per-route throw endpoints.`));
  }
  v.appendChild(rp);
  return v;
}

/* ---- helpers ---- */
function mkSelect(label,opts,cur,onchange){
  const w=el("label"); w.innerHTML=label+" ";
  const s=el("select");
  opts.forEach(o=>{const op=el("option",null,o); op.value=o; if(o===cur)op.selected=true; s.appendChild(op);});
  s.onchange=()=>onchange(s.value); w.appendChild(s); return w;
}
function renderInto(panel, fn){ fn(panel); }

function render(){
  const view=document.getElementById("view"); view.innerHTML="";
  if(TAB==="players") view.appendChild(viewPlayers());
  else if(TAB==="overview") view.appendChild(viewOverview());
  else if(TAB==="stayorgo") view.appendChild(viewStayGo());
}

function init(){
  renderTabs(); setupMode();
  document.getElementById("prov").innerHTML =
    "<b>Source files (read-only):</b><br>"+DATA.provenance.map(f=>"\u2022 "+f).join("<br>");
  render();
}
init();
</script>
</body>
</html>
"""
