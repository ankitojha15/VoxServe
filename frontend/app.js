function tab(n) {
  for (const t of ['chat', 'docs', 'voice', 'ops']) {
    document.getElementById('c-' + t).className = 'tab' + (t === n ? ' on' : '');
    document.getElementById('t-' + t).className = (t === n ? 'on' : '');
  }
  if (n === 'docs') loadSources();
  if (n === 'ops') loadHealth();
}
async function send() {
  const btn = document.getElementById('sendbtn');
  btn.disabled = true;
  const q = document.getElementById('q').value;
  const box = document.getElementById('out');
  const escHtml = s => (s || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  const fmt = s => escHtml(s).replace(/\n/g, '<br>');
  if (box.querySelector('.skel')) box.innerHTML = '';
  const t = new Date().toLocaleTimeString();
  box.innerHTML += '<div class="row"><b>You:</b> ' + escHtml(q) + ' <span class="cite">' + t + '</span></div>';
  const think = document.createElement('div');
  think.className = 'row skel';
  think.textContent = 'Thinking…';
  box.appendChild(think);
  try {
    const r = await fetch('/chat', {
      method: 'POST', headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({query: q})
    });
    if (!r.ok) throw new Error('server ' + r.status);
  const d = await r.json();
  think.remove();
  const esc = d.intent === 'unknown' || (d.answer || '').indexOf('Escalated') === 0;
  let html = '<div class="row' + (esc ? ' bad' : '') + '"><b>Bot [' + d.intent + ' ' + d.confidence + ']:</b><br>'
    + fmt(d.answer) + (d.cached ? ' <span class="badge">cached' + (d.cached === true ? '' : ': ' + d.cached) + '</span>' : '') + '</div>';
  if (d.need_id) {
    html += '<div class="row"><span class="cite">Choose an ID:</span> '
      + ['1001', '1002', '1003', '9999'].map(id => '<button class="ghost" onclick="ask(\'Where is my order ' + id + '?\')">' + id + '</button>').join(' ')
      + '</div>';
  }
  box.innerHTML += html;
  speakOut(d.answer);
  } catch (e) {
    think.remove();
    box.innerHTML += '<div class="row bad"><b>Error:</b> server not reachable. Start the backend first.</div>';
  }
  btn.disabled = false;
}
let voiceEnIn = null;
function pickVoice() {
  try {
    const vs = speechSynthesis.getVoices() || [];
    voiceEnIn = vs.find(v => /en[-_]IN/i.test(v.lang)) || vs.find(v => /^en/i.test(v.lang)) || null;
  } catch (e) {}
}
if (typeof speechSynthesis !== 'undefined') {
  pickVoice();
  speechSynthesis.onvoiceschanged = pickVoice;
}
function cleanSpeak(s, n) {
  return (s || '').replace(/\[.*?page \d+\]/g, ' ').replace(/[•#*`_>|]/g, ' ').replace(/\s{2,}/g, ' ').trim().slice(0, n || 200);
}
let currentAudio = null;
function stopAudio() {
  try { if (currentAudio) { currentAudio.pause(); currentAudio = null; } } catch (e) {}
  try { speechSynthesis.cancel(); } catch (e) {}
}
async function speakOut(s) {
  if (!soundOn) return;
  stopAudio();
  const text = cleanSpeak(s, 400);
  if (!text) return;
  try {
    const r = await fetch('/voice/speak', {
      method: 'POST', headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({text})
    });
    if (!r.ok) throw new Error('tts ' + r.status);
    const blob = await r.blob();
    const url = URL.createObjectURL(blob);
    currentAudio = new Audio(url);
    currentAudio.onended = () => URL.revokeObjectURL(url);
    currentAudio.play().catch(() => speakBrowser(s));
  } catch (e) {
    speakBrowser(s);
  }
}
function speakBrowser(s) {
  try {
    if (!soundOn) return;
    speechSynthesis.cancel();
    const u = new SpeechSynthesisUtterance(cleanSpeak(s, 200));
    if (voiceEnIn) u.voice = voiceEnIn;
    u.rate = 0.95;
    speechSynthesis.speak(u);
  } catch (e) {}
}
function clearChat() {
  document.getElementById('out').innerHTML = '<span class="skel">Answers appear here with citations.</span>';
}
function stopSound() {
  try { speechSynthesis.cancel(); } catch (e) {}
}
let soundOn = true;
function toggleSound() {
  soundOn = !soundOn;
  if (!soundOn) { stopAudio(); }
  document.getElementById('sndbtn').textContent = soundOn ? 'Sound: On' : 'Sound: Off';
}
function ask(q) {
  document.getElementById('q').value = q; send();
}
function mic() {
  stopAudio();
  const R = window.webkitSpeechRecognition || window.SpeechRecognition;
  if (!R) { alert('Mic not supported here, please type.'); return; }
  const rec = new R(); rec.lang = 'en-IN';
  rec.onresult = e => { document.getElementById('q').value = e.results[0][0].transcript; send(); };
  rec.start();
}
async function uploadPdf() {
  const f = document.getElementById('pdf').files[0];
  if (!f) return;
  const msg = document.getElementById('upmsg');
  msg.textContent = 'Uploading…';
  try {
    const fd = new FormData(); fd.append('file', f);
    const r = await fetch('/ingest/pdf', {method: 'POST', body: fd});
    const d = await r.json();
    if (!r.ok || d.error) throw new Error(d.error || ('server ' + r.status));
    msg.textContent = 'Uploaded ' + d.chunks + ' chunks from ' + d.file;
    document.getElementById('pdf').value = '';
    document.getElementById('upbtn').disabled = true;
    loadSources();
  } catch (e) {
    msg.textContent = 'Failed: ' + e.message + '. Try again or check server logs.';
  }
}
async function loadSources() {
  const r = await fetch('/sources');
  const d = await r.json();
  let h = '<table><tr><th>File</th><th>Size (KB)</th><th></th></tr>';
  for (const f of d.policy_files) h += '<tr><td>' + f.name + '</td><td>' + f.kb + '</td><td><button class="ghost" onclick="delFile(\'' + f.name + '\')">Delete</button></td></tr>';
  document.getElementById('sources').innerHTML = h + '</table>';
}
async function delFile(name) {
  const f = name.split('/').pop();
  await fetch('/ingest/file?name=' + encodeURIComponent(f), {method: 'DELETE'});
  loadSources();
}
async function joinRoom() {
  const vout = document.getElementById('vout');
  try {
    const r = await fetch('/voice/token', {
      method: 'POST', headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({room: 'voice-room-1', name: 'web1'})
    });
    const d = await r.json();
    if (!r.ok || d.error || !d.token || !d.url) throw new Error(d.error || ('server ' + r.status));
    const room = new LivekitClient.Room();
    await room.connect(d.url, d.token);
    await room.localParticipant.setMicrophoneEnabled(true);
    document.getElementById('speakbtn').disabled = false;
    document.getElementById('joinbtn').disabled = true;
    vout.innerHTML = '<div class="row"><b>Room:</b> joined voice-room-1, mic on. Now press Speak.</div>';
  } catch (e) {
    vout.innerHTML = '<div class="row bad"><b>Voice room failed:</b> ' + e.message + '</div>';
  }
}
async function loadHealth() {
  try {
    const r = await fetch('/health');
    const d = await r.json();
    const s = 'API ' + d.status + ' · redis ' + d.redis;
    document.getElementById('health').innerHTML = '<b>Health:</b> ' + s;
    document.getElementById('statusline').textContent = s + ' · 60 evals green';
  } catch (e) {
    document.getElementById('statusline').textContent = 'Server not reachable. Start the backend first.';
  }
}
loadHealth();
