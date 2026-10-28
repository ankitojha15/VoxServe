/* VoxServe console app */
"use strict";

const $ = id => document.getElementById(id);
const esc = s => (s || "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");

/* ---------- status ---------- */
function setServerState(cls, text) {
  const dot = $("dot");
  dot.className = "dot" + (cls ? " " + cls : "");
  $("statusline").textContent = text;
}
async function checkHealth() {
  try {
    const r = await fetch("/health", {signal: AbortSignal.timeout(5000)});
    if (!r.ok) return null;
    return await r.json();
  } catch (e) { return null; }
}
async function healthLoop() {
  let d = await checkHealth();
  let tries = 0;
  while (!d && tries < 40) {
    tries++;
    setServerState("", tries < 8 ? "waking (free tier ~50s)…" : "offline — start the backend");
    $("health").innerHTML = '<span class="skel">waiting for server…</span>';
    await new Promise(res => setTimeout(res, 3000));
    d = await checkHealth();
  }
  if (d) {
    const s = d.redis === "up" ? "api up · redis up" : "api up · redis down";
    setServerState(d.redis === "up" ? "ok" : "err", s);
    $("health").innerHTML = '<span class="kv"><b>API</b><span class="mono">' + d.status + '</span></span>'
      + '<span class="kv"><b>Redis</b><span class="mono">' + d.redis + '</span></span>';
  } else {
    setServerState("err", "offline");
    $("health").innerHTML = '<span class="empty">Server not reachable.</span>';
  }
  setTimeout(healthLoop, 15000);
}

/* ---------- tabs ---------- */
function tab(n) {
  const titles = {chat: "Chat", docs: "Docs", voice: "Voice", ops: "Ops"};
  document.title = "VoxServe — " + titles[n];
  for (const t of ["chat", "docs", "voice", "ops"]) {
    $("c-" + t).className = "tab" + (t === n ? " on" : "");
    $("t-" + t).className = "nav-btn" + (t === n ? " on" : "");
    $("t-" + t).setAttribute("aria-current", t === n ? "page" : "false");
  }
  if (n === "docs") loadSources();
  if (n === "ops") { loadEvals(); drawSpark(); loadAudit(); }
}

/* ---------- context panel ---------- */
function ctxEmpty() {
  $("ctx").innerHTML = '<div class="empty">Order details and citation sources appear here.</div>';
}
function showOrder(oid, status, tracking) {
  const cls = {shipped: "ok", delivered: "ok", stuck: "warn", not_found: "err"}[status] || "";
  $("ctx").innerHTML =
    '<div class="kv"><b>Order</b><span class="mono">' + esc(oid) + '</span></div>'
    + '<div class="kv"><b>Status</b><span class="badge ' + cls + '">' + esc(status) + '</span></div>'
    + '<div class="kv"><b>Tracking</b><span class="mono">' + esc(tracking || "-") + '</span></div>';
}
function showSource(file, page) {
  const url = "https://github.com/ankitojha15/VoxServe/blob/main/data/raw/" + encodeURIComponent(file);
  $("ctx").innerHTML =
    '<div class="kv"><b>Source</b><span class="mono">' + esc(file) + '</span></div>'
    + '<div class="kv"><b>Page</b><span class="mono">' + esc(page) + '</span></div>'
    + '<div style="margin-top:8px;"><a class="cite" href="' + url + '" target="_blank" rel="noopener">Open file on GitHub</a></div>';
}

/* ---------- conversation ---------- */
const CITE_RE = /\[([A-Za-z0-9_\-\.]+\.(?:md|pdf)) page (\d+)\]/g;

function addMsg(who, cls) {
  const m = document.createElement("div");
  m.className = "msg" + (cls ? " " + cls : "");
  m.innerHTML = '<span class="who">' + esc(who) + '</span><span class="cite">' + new Date().toLocaleTimeString() + '</span>'
    + '<div class="msg-body"></div><div class="chips"></div>';
  $("out").appendChild(m);
  const empty = $("out").querySelector(".empty");
  if (empty) empty.remove();
  return m;
}
function chip(label, cls) {
  const b = document.createElement("span");
  b.className = "badge" + (cls ? " " + cls : "");
  b.textContent = label;
  return b;
}
function addCitationChips(container, text) {
  let m;
  const seen = new Set();
  while ((m = CITE_RE.exec(text))) {
    const key = m[1] + "#" + m[2];
    if (seen.has(key)) continue;
    seen.add(key);
    const c = document.createElement("button");
    c.className = "cite-chip";
    c.textContent = m[1] + " p" + m[2];
    c.onclick = () => showSource(m[1], m[2]);
    container.appendChild(c);
  }
  return text.replace(/(\n*)\[([A-Za-z0-9_\-\.]+\.(?:md|pdf)) page \d+\](\n*)/g, "").trim();
}

async function sendOnce(query) {
  const r = await fetch("/chat", {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({query}),
    signal: AbortSignal.timeout(90000),
  });
  if (!r.ok) throw new Error("server " + r.status);
  return r.json();
}

async function send() {
  const ta = $("q");
  const q = ta.value.trim();
  if (!q) return;
  const btn = $("sendbtn");
  btn.disabled = true;
  ta.value = "";

  const um = addMsg("You");
  um.querySelector(".msg-body").textContent = q;

  const bm = addMsg("VoxServe");
  const bodyEl = bm.querySelector(".msg-body");
  bodyEl.innerHTML = '<span class="skel">Thinking…</span>';
  setVState("thinking");

  const t0 = performance.now();
  let d, lastErr = null;
  for (let i = 0; i < 3; i++) {
    try { d = await sendOnce(q); lastErr = null; break; }
    catch (e) {
      lastErr = e;
      if (e.name === "AbortError") break;
      bodyEl.textContent = "Waking server (free tier ~50s)… retry " + (i + 1) + "/3";
      await new Promise(res => setTimeout(res, 20000));
    }
  }

  const ms = Math.round(performance.now() - t0);
  pushLatency(ms);

  if (lastErr || !d) {
    bodyEl.textContent = "Server not reachable. Free tier sleeps ~50s — wait a moment and send again.";
    bm.classList.add("escalated");
    setVState("idle");
    btn.disabled = false;
    return;
  }

  const escalated = d.intent === "unknown" || (d.answer || "").indexOf("Escalated") === 0;
  const body = addCitationChips(bm.querySelector(".chips"), d.answer || "");
  bodyEl.textContent = body;
  if (escalated) bm.classList.add("escalated");

  const chips = bm.querySelector(".chips");
  chips.appendChild(chip(d.intent, {order: "ok", ticket: "warn", unknown: "err"}[d.intent] || ""));
  chips.appendChild(chip("conf " + (d.confidence ?? "-")));
  chips.appendChild(chip(ms + "ms"));
  if (d.cached) chips.appendChild(chip("cached" + (d.cached === true ? "" : ": " + d.cached), "ok"));
  const copy = document.createElement("button");
  copy.className = "link-btn";
  copy.textContent = "copy";
  copy.onclick = () => navigator.clipboard.writeText(d.answer || "");
  chips.appendChild(copy);

  if (d.need_id) {
    const row = document.createElement("div");
    row.className = "chips";
    row.innerHTML = '<span class="cite">Choose an ID:</span>';
    for (const id of ["1001", "1002", "1003", "9999"]) {
      const b = document.createElement("button");
      b.className = "ghost";
      b.textContent = id;
      b.onclick = () => { ta.value = "Where is my order " + id + "?"; send(); };
      row.appendChild(b);
    }
    bm.appendChild(row);
  }

  const om = /Order (\d+) status: ([a-z_]+), tracking: ([A-Za-z0-9-]+)/i.exec(d.answer || "");
  if (om) showOrder(om[1], om[2], om[3]);
  else if (d.intent === "policy" || d.intent === "unknown") ctxEmpty();

  setVState("idle");
  speakOut(d.answer || "");
  btn.disabled = false;
  ta.focus();
}

/* ---------- voice / TTS ---------- */
let voiceEnIn = null, soundOn = true, currentAudio = null;
function pickVoice() {
  try {
    const vs = speechSynthesis.getVoices() || [];
    voiceEnIn = vs.find(v => /en[-_]IN/i.test(v.lang)) || vs.find(v => /^en/i.test(v.lang)) || null;
  } catch (e) {}
}
if (typeof speechSynthesis !== "undefined") {
  pickVoice();
  speechSynthesis.onvoiceschanged = pickVoice;
}
function cleanSpeak(s, n) {
  return (s || "").replace(/\[.*?page \d+\]/g, " ").replace(/[•#*`_>|]/g, " ").replace(/\s{2,}/g, " ").trim().slice(0, n || 200);
}
function setVState(s) {
  const map = {idle: ["", "idle"], listening: ["ok", "listening…"], thinking: ["warn", "thinking…"], speaking: ["ok", "speaking…"]};
  const [cls, text] = map[s] || map.idle;
  const dot = $("vdot");
  if (dot) {
    dot.className = "dot" + (cls ? " " + cls : "") + (s === "listening" ? " pulse" : "");
    $("vstate").textContent = text;
  }
}
function stopAudio() {
  try { if (currentAudio) { currentAudio.pause(); currentAudio = null; } } catch (e) {}
  try { speechSynthesis.cancel(); } catch (e) {}
  setVState("idle");
}
async function speakOut(s) {
  if (!soundOn) return;
  stopAudio();
  const text = cleanSpeak(s, 400);
  if (!text) return;
  setVState("speaking");
  try {
    const r = await fetch("/voice/speak", {
      method: "POST", headers: {"Content-Type": "application/json"},
      body: JSON.stringify({text}),
      signal: AbortSignal.timeout(30000),
    });
    if (!r.ok) throw new Error("tts " + r.status);
    const url = URL.createObjectURL(await r.blob());
    currentAudio = new Audio(url);
    currentAudio.onended = () => { URL.revokeObjectURL(url); setVState("idle"); };
    currentAudio.play().catch(() => { speakBrowser(text); setVState("idle"); });
  } catch (e) {
    speakBrowser(text);
    setVState("idle");
  }
}
function speakBrowser(s) {
  try {
    if (!soundOn) return;
    speechSynthesis.cancel();
    const u = new SpeechSynthesisUtterance(cleanSpeak(s, 200));
    if (voiceEnIn) u.voice = voiceEnIn;
    u.rate = 0.95;
    u.onend = () => setVState("idle");
    speechSynthesis.speak(u);
  } catch (e) {}
}
function mic() {
  stopAudio();
  const R = window.webkitSpeechRecognition || window.SpeechRecognition;
  if (!R) { alert("Mic not supported here, please type."); return; }
  const rec = new R();
  rec.lang = "en-IN";
  setVState("listening");
  rec.onresult = e => {
    $("q").value = e.results[0][0].transcript;
    send();
  };
  rec.onerror = () => setVState("idle");
  rec.onend = () => { if ($("vstate").textContent === "listening…") setVState("idle"); };
  rec.start();
}

/* ---------- docs ---------- */
function sourceRowHTML(f) {
  const name = f.name.split("/").pop();
  return '<tr><td class="mono">' + esc(name) + '</td><td class="mono">' + f.kb + '</td>'
    + '<td><button class="ghost" data-del="' + esc(name) + '">Delete</button></td></tr>';
}
async function loadSources() {
  $("sources").innerHTML = '<span class="skel">Loading…</span>';
  try {
    const d = await (await fetch("/sources")).json();
    if (!d.policy_files.length) {
      $("sources").innerHTML = '<span class="empty">No files yet.</span>';
    } else {
      $("sources").innerHTML = '<table><tr><th>File</th><th>KB</th><th></th></tr>'
        + d.policy_files.map(sourceRowHTML).join("") + '</table>';
    }
    $("psources").innerHTML = d.policy_files.length
      ? d.policy_files.map(f => '<div class="kv"><b>file</b><span class="mono">' + esc(f.name.split("/").pop()) + '</span></div>').join("")
      : '<div class="empty">None.</div>';
    for (const b of $("sources").querySelectorAll("[data-del]")) {
      b.onclick = () => delFile(b.dataset.del);
    }
  } catch (e) {
    $("sources").innerHTML = '<span class="empty">Load failed.</span>';
  }
}
async function delFile(name) {
  await fetch("/ingest/file?name=" + encodeURIComponent(name), {method: "DELETE"});
  loadSources();
}
async function uploadPdf() {
  const f = $("pdf").files[0];
  if (!f) return;
  const msg = $("upmsg");
  msg.textContent = "Uploading…";
  try {
    const fd = new FormData();
    fd.append("file", f);
    const r = await fetch("/ingest/pdf", {method: "POST", body: fd, signal: AbortSignal.timeout(120000)});
    const d = await r.json();
    if (!r.ok || d.error) throw new Error(d.error || "server " + r.status);
    msg.textContent = "Uploaded " + d.chunks + " chunks from " + d.file;
    $("pdf").value = "";
    $("upbtn").disabled = true;
    loadSources();
  } catch (e) {
    msg.textContent = "Failed: " + e.message;
  }
}

/* ---------- livekit (advanced) ---------- */
async function joinRoom() {
  const vout = $("vout");
  try {
    const d = await (await fetch("/voice/token", {
      method: "POST", headers: {"Content-Type": "application/json"},
      body: JSON.stringify({room: "voice-room-1", name: "web1"}),
    })).json();
    if (!d.token || !d.url) throw new Error(d.error || "no token");
    const room = new LivekitClient.Room();
    await room.connect(d.url, d.token);
    await room.localParticipant.setMicrophoneEnabled(true);
    vout.innerHTML = '<div class="row">Joined <span class="mono">voice-room-1</span>, mic on.</div>';
  } catch (e) {
    vout.innerHTML = '<div class="row" style="color:var(--err)">Room failed: ' + esc(e.message) + '</div>';
  }
}

/* ---------- ops ---------- */
async function loadEvals() {
  const box = $("evals");
  try {
    const e = await (await fetch("/static/eval-latest.json", {cache: "no-store"})).json();
    const pc = o => (o.n ? (o.ok / o.n).toFixed(2) : "-");
    box.innerHTML =
      '<div class="kv"><b>Run</b><span>' + esc(e.run) + '</span></div>'
      + '<div class="kv"><b>Tool acc</b><span class="mono">' + e.tool.ok + '/' + e.tool.n + ' = ' + pc(e.tool) + '</span></div>'
      + '<div class="kv"><b>Faithfulness</b><span class="mono">' + e.faith.ok + '/' + e.faith.n + ' = ' + pc(e.faith) + '</span></div>'
      + '<div class="kv"><b>Unsafe block</b><span class="mono">' + e.unsafe.ok + '/' + e.unsafe.n + '</span></div>'
      + '<div class="kv"><b>p95 text</b><span class="mono">' + e.p95_text_s + 's</span></div>'
      + '<div style="margin-top:8px;"><span class="badge ' + (e.gate === "PASS" ? "ok" : "err") + '">gate ' + esc(e.gate) + '</span></div>';
  } catch (e2) {
    box.innerHTML = '<span class="empty">No eval file yet. Run: python -m backend.eval50</span>';
  }
}
async function loadAudit() {
  const box = $("audit");
  try {
    const d = await (await fetch("/audit/tail", {cache: "no-store"})).json();
    if (!d.entries.length) { box.innerHTML = '<span class="empty">No audit entries yet. Use the chat, then refresh.</span>'; return; }
    box.innerHTML = '<table><tr><th>Time</th><th>Tool</th><th>Args</th><th>Status</th></tr>'
      + d.entries.map(a =>
        '<tr><td class="mono">' + esc(String(a.ts).slice(0, 19)) + '</td>'
        + '<td class="mono">' + esc(a.tool) + '</td>'
        + '<td class="mono">' + esc(a.args) + '</td>'
        + '<td class="mono">' + esc(a.status) + '</td></tr>').join("")
      + '</table>';
  } catch (e) {
    box.innerHTML = '<span class="empty">Audit not available.</span>';
  }
}
const LAT_KEY = "vox_lat";
function pushLatency(ms) {
  let arr = [];
  try { arr = JSON.parse(localStorage.getItem(LAT_KEY) || "[]"); } catch (e) {}
  arr.push(ms);
  if (arr.length > 50) arr = arr.slice(-50);
  try { localStorage.setItem(LAT_KEY, JSON.stringify(arr)); } catch (e) {}
  if ($("c-ops").classList.contains("on")) drawSpark();
}
function drawSpark() {
  let arr = [];
  try { arr = JSON.parse(localStorage.getItem(LAT_KEY) || "[]"); } catch (e) {}
  const stats = $("latstats");
  if (!arr.length) { stats.textContent = "no data yet — send a chat first"; return; }
  const s = [...arr].sort((a, b) => a - b);
  const p95 = s[Math.floor(0.95 * (s.length - 1))];
  const avg = Math.round(s.reduce((x, y) => x + y, 0) / s.length);
  stats.textContent = "n=" + arr.length + " · avg " + avg + "ms · p95 " + p95 + "ms (client-measured)";
  const cv = $("spark");
  const c = cv.getContext("2d");
  c.clearRect(0, 0, cv.width, cv.height);
  const max = Math.max(...arr, 100), W = cv.width, H = cv.height, pad = 4;
  c.strokeStyle = getComputedStyle(document.documentElement).getPropertyValue("--accent").trim() || "#1663d6";
  c.lineWidth = 1.5;
  c.beginPath();
  arr.forEach((ms2, i) => {
    const x = pad + (i / Math.max(arr.length - 1, 1)) * (W - 2 * pad);
    const y = H - pad - (ms2 / max) * (H - 2 * pad);
    i ? c.lineTo(x, y) : c.moveTo(x, y);
  });
  c.stroke();
}

/* ---------- wire up ---------- */
$("sendbtn").onclick = send;
$("micbtn").onclick = mic;
$("micbtn2").onclick = mic;
$("clearbtn").onclick = () => { $("out").innerHTML = '<div class="empty">Answers appear here with citations.</div>'; ctxEmpty(); };
$("sndbtn").onclick = () => {
  soundOn = !soundOn;
  if (!soundOn) stopAudio(); else setVState("idle");
  $("sndbtn").textContent = soundOn ? "Sound: On" : "Sound: Off";
};
$("q").addEventListener("keydown", e => {
  if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(); }
});
$("q").addEventListener("input", () => {
  const ta = $("q");
  ta.style.height = "auto";
  ta.style.height = Math.min(ta.scrollHeight, 140) + "px";
});
for (const b of document.querySelectorAll(".nav-btn")) b.onclick = () => tab(b.dataset.tab);
for (const b of document.querySelectorAll("[data-q]")) b.onclick = () => { $("q").value = b.dataset.q; send(); };
$("pdf").onchange = () => { $("upbtn").disabled = !$("pdf").files.length; };
$("upbtn").onclick = uploadPdf;
$("srcbtn").onclick = loadSources;
$("joinbtn").onclick = joinRoom;
document.addEventListener("keydown", e => {
  if (e.key === "Escape") stopAudio();
  if (e.key === "/" && document.activeElement !== $("q")) { e.preventDefault(); $("q").focus(); }
});

healthLoop();
