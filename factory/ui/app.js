/* Editing factory console. Vanilla JS, no build step. Every dynamic string goes in through textContent (h()), never innerHTML. */
(() => {
'use strict';

const TOKEN = (document.querySelector('meta[name="factory-token"]') || {}).content || '';
const view = document.getElementById('view');
const crumb = document.getElementById('crumb');
const LANES = [
  ['all', 'All', null],
  ['arriving', 'Arriving', ['new', 'transcribing', 'detecting']],
  ['needs', 'Needs your yes', ['proposed']],
  ['editing', 'Editing', ['approved', 'editing', 'changes']],
  ['review', 'With the reviewer', ['in_review']],
  ['finished', 'Finished', ['done', 'rejected']],
];
const STAGES = [['new', 'New'], ['transcribing', 'Listening'], ['detecting', 'Theme'], ['proposed', 'Proposal'],
  ['approved', 'Approved'], ['editing', 'Editing'], ['in_review', 'Review'], ['done', 'Done']];
const STATUS_LABEL = {new: 'New', transcribing: 'Transcribing', detecting: 'Detecting theme', proposed: 'Needs your yes',
  approved: 'Approved', editing: 'Editing', in_review: 'In review', changes: 'Changes asked', done: 'Done', rejected: 'Rejected'};
const STUCK_HOURS = 24;
const NAV = [['/', 'Reels', 'reels', 'Work'], ['/review', 'Daily review', 'review', ''],
  ['/agents', 'Agents', 'agents', 'Setup'], ['/themes', 'Themes', 'themes', ''], ['/assets', 'Assets', 'assets', '']];

/* ---------- tiny helpers ---------- */
function h(tag, attrs, ...kids) {
  const e = document.createElement(tag);
  for (const k in attrs || {}) {
    const v = attrs[k];
    if (v == null || v === false) continue;
    if (k === 'class') e.className = v;
    else if (k.startsWith('on')) e.addEventListener(k.slice(2), v);
    else e.setAttribute(k, v === true ? '' : v);
  }
  for (const c of kids.flat(Infinity)) {
    if (c == null || c === false) continue;
    e.append(c.nodeType ? c : document.createTextNode(String(c)));
  }
  return e;
}
const PATHS = {
  reels: '<rect x="2" y="3" width="12" height="10" rx="2"/><path d="M6 3v10M10 3v10M2 8h12"/>',
  review: '<path d="M4 2.5h8v11H4z"/><path d="M6.5 6h3M6.5 9h3"/>',
  agents: '<circle cx="8" cy="6" r="2.5"/><path d="M3 13c.6-2.4 2.6-3.5 5-3.5s4.4 1.1 5 3.5"/>',
  themes: '<path d="M2.5 8.5V3h5.5l5.5 5.5-5.5 5.5z"/><circle cx="5.5" cy="5.5" r=".6"/>',
  assets: '<path d="M6 12V4l7-1.5v8"/><circle cx="4.5" cy="12" r="1.5"/><circle cx="11.5" cy="10.5" r="1.5"/>',
  x: '<path d="M4 4l8 8M12 4l-8 8"/>', check: '<path d="M3.5 8.5l3 3 6-7"/>',
  alert: '<circle cx="8" cy="8" r="6"/><path d="M8 5v3.5M8 11v.01"/>', info: '<circle cx="8" cy="8" r="6"/><path d="M8 7.5V11M8 5v.01"/>',
  sun: '<circle cx="8" cy="8" r="2.5"/><path d="M8 2v1.5M8 12.5V14M2 8h1.5M12.5 8H14M3.8 3.8l1 1M11.2 11.2l1 1M3.8 12.2l1-1M11.2 4.8l1-1"/>',
  moon: '<path d="M13 9.5A5.5 5.5 0 016.5 3 5.5 5.5 0 1013 9.5z"/>',
  monitor: '<rect x="2" y="3" width="12" height="8" rx="1.5"/><path d="M6 14h4M8 11v3"/>',
  copy: '<rect x="5.5" y="5.5" width="8" height="8" rx="1.5"/><path d="M10.5 5.5v-2a1 1 0 00-1-1h-6a1 1 0 00-1 1v6a1 1 0 001 1h2"/>',
  empty: '<path d="M2.5 8.5l2-5h7l2 5v4h-11z"/><path d="M2.5 8.5h3l1 1.5h3l1-1.5h3"/>',
  wifi: '<path d="M2 6.5a9 9 0 0112 0M4.5 9a5.5 5.5 0 017 0M7 11.5a2 2 0 012 0"/>',
};
function ic(name) {
  const s = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
  s.setAttribute('class', 'i'); s.setAttribute('viewBox', '0 0 16 16'); s.setAttribute('aria-hidden', 'true');
  s.innerHTML = PATHS[name] || '';  // constants above only
  return s;
}
const sleep = ms => new Promise(r => setTimeout(r, ms));
const pct = x => Math.round((+x || 0) * 100) + '%';
const reduced = () => matchMedia('(prefers-reduced-motion: reduce)').matches;

function when(iso) {  // "13:33" today, "10/29 13:33" before: never a raw ISO string
  const d = new Date(iso);
  if (isNaN(d)) return '';
  const hm = String(d.getHours()).padStart(2, '0') + ':' + String(d.getMinutes()).padStart(2, '0');
  return d.toDateString() === new Date().toDateString() ? hm : `${d.getMonth() + 1}/${d.getDate()} ${hm}`;
}
function ago(iso) {
  const d = new Date(iso);
  if (isNaN(d)) return '';
  const m = (Date.now() - d) / 60000;
  if (m < 1) return 'Just now';
  if (m < 60) return Math.round(m) + 'm ago';
  if (m < 1440 && d.toDateString() === new Date().toDateString()) return Math.floor(m / 60) + 'h ago';
  const days = Math.round((new Date().setHours(0, 0, 0, 0) - new Date(d).setHours(0, 0, 0, 0)) / 864e5);
  return days <= 1 ? 'Yesterday' : days + ' days ago';
}
const hoursSince = iso => (Date.now() - new Date(iso)) / 36e5;

/* ---------- routing: the URL is the state ---------- */
function parse() {
  const p = new URLSearchParams(location.search);
  const m = location.pathname.match(/^\/reels\/([^/]+)$/);
  const sec = m || location.pathname === '/' || location.pathname === '/reels' ? 'reels' : location.pathname.slice(1);
  return {sec, id: m ? decodeURIComponent(m[1]) : '', p};
}
function href(path, params) {
  const q = new URLSearchParams();
  for (const [k, v] of Object.entries(params || {})) if (v) q.set(k, v);
  const s = q.toString();
  return path + (s ? '?' + s : '');
}
function go(url, replace) {
  history[replace ? 'replaceState' : 'pushState'](null, '', url);
  render();
}
document.addEventListener('click', e => {
  const a = e.target.closest && e.target.closest('a[href^="/"]');
  if (!a || e.defaultPrevented || e.button || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey || a.target) return;
  e.preventDefault();
  go(a.getAttribute('href'));
});
addEventListener('popstate', render);
addEventListener('keydown', e => {
  if (e.key !== 'Escape' || dlg.open) return;
  const {id} = parse();
  if (id) go(href('/', filterParams()));  // Esc closes the top layer: here the open record
});

/* ---------- api, toasts, dialog ---------- */
async function api(path, body, signal) {
  const opt = {signal, headers: {}};
  if (body !== undefined) {
    opt.method = 'POST';
    opt.headers = {'Content-Type': 'application/json', 'X-Factory-Token': TOKEN};
    opt.body = JSON.stringify(body);
  }
  let res;
  try { res = await fetch(path, opt); } catch (e) { const err = new Error(e.name === 'AbortError' ? 'The request was stopped.' : 'Could not reach the factory.'); err.net = e.name !== 'AbortError'; throw err; }
  let data = null;
  try { data = await res.json(); } catch (e) { /* not json */ }
  if (!res.ok) { const err = new Error((data && data.error) || 'Something went wrong.'); err.status = res.status; throw err; }
  return data;
}
function toast(kind, title, msg) {
  const t = h('div', {class: 'toast ' + kind}, ic(kind === 'error' ? 'alert' : kind === 'success' ? 'check' : 'info'),
    h('div', null, h('b', null, title), msg ? h('span', null, msg) : null));
  document.getElementById('toasts').append(t);
  setTimeout(() => { t.classList.add('out'); setTimeout(() => t.remove(), 180); }, 3000);
}
const dlg = document.getElementById('dlg');
let opener = null;
function openDialog(content) {
  opener = document.activeElement;
  dlg.replaceChildren(content);
  dlg.showModal();
  requestAnimationFrame(() => dlg.classList.add('open'));
  const f = dlg.querySelector('textarea, button.choice-first') || dlg.querySelector('button');
  if (f) f.focus();
}
function closeDialog() {
  dlg.classList.remove('open'); dlg.classList.add('closing');
  setTimeout(() => { dlg.close(); dlg.classList.remove('closing'); if (opener && opener.isConnected) opener.focus(); }, reduced() ? 0 : 180);
}
dlg.addEventListener('cancel', e => { e.preventDefault(); closeDialog(); });
dlg.addEventListener('click', e => { if (e.target === dlg) closeDialog(); });

/* ---------- states: skeleton at the final shape, empty, error ---------- */
let seq = 0;
function skel(kind) {
  const sk = (w, hgt) => { const e = h('div', {class: 'sk'}); e.style.width = w; e.style.height = hgt + 'px'; return e; };
  const rows = (n, hgt) => Array.from({length: n}, () => sk('100%', hgt));
  if (kind === 'cards') return h('div', {class: 'bento'}, Array.from({length: 6}, () => h('div', {class: 'card tile s4'}, sk('50%', 20), sk('100%', 32), ...rows(3, 24))));
  if (kind === 'review') return h('div', {class: 'bento'}, Array.from({length: 4}, () => h('div', {class: 'card tile s6'}, sk('40%', 20), ...rows(3, 32))));
  return h('div', null, h('div', {class: 'head skel'}, sk('160px', 36), sk('240px', 16)), sk('100%', 40),
    h('div', {class: 'cols sk-table'}, h('div', {class: 'skel s12'}, ...rows(7, 40))));
}
function stateBox(kind, title, text, actionLabel, action) {
  return h('div', {class: 'card'}, h('div', {class: 'state' + (kind === 'err' ? ' err' : '')},
    h('div', {class: 'mark'}, ic(kind === 'err' ? 'wifi' : 'empty')), h('h2', null, title), h('p', null, text),
    actionLabel ? h('button', {class: 'btn', type: 'button', onclick: action}, actionLabel) : null));
}
/* 0-300 ms nothing, then a skeleton held >= 400 ms; 10 s "Still working" + Cancel; 15 s stop and offer Retry */
async function guarded(fetcher, kind) {
  const my = ++seq, ctl = new AbortController();
  let shown = 0;
  const t1 = setTimeout(() => { if (my === seq) { view.replaceChildren(skel(kind)); shown = Date.now(); } }, 300);
  const t2 = setTimeout(() => { if (my === seq && shown) view.append(h('div', {class: 'stillwork'}, 'Still working...', h('button', {class: 'btn sm', type: 'button', onclick: () => ctl.abort()}, 'Cancel'))); }, 10000);
  const t3 = setTimeout(() => ctl.abort(), 15000);
  try {
    const data = await fetcher(ctl.signal);
    if (shown) await sleep(Math.max(0, 400 - (Date.now() - shown)));
    return my === seq ? {data} : null;
  } catch (e) {
    if (my !== seq) return null;
    view.replaceChildren(head(({reels: 'Reels', review: 'Daily review', agents: 'Agents', themes: 'Themes', assets: 'Assets'})[parse().sec] || 'Editing factory', ''), stateBox('err', "Couldn't load this page",
      e.net ? 'The connection to the factory dropped. Your reels and files on disk are untouched.' : e.message, 'Try again', render));
    return null;
  } finally { clearTimeout(t1); clearTimeout(t2); clearTimeout(t3); }
}
function head(title, sub, ...actions) {
  return h('div', {class: 'head'}, h('div', null, h('h1', null, title), sub ? h('p', null, sub) : null), actions.length ? h('div', {class: 'acts'}, actions) : null);
}

/* ---------- pieces ---------- */
function badge(r) {
  let label = STATUS_LABEL[r.status] || r.status, cls = 'badge quiet';
  if (r.status === 'proposed') {
    if (r.decided) label = r.decided === 'approved' ? 'Approved' : 'Rejected';
    else if (r.awaiting_you) cls = 'badge act';
  } else if (r.status === 'in_review') cls = 'badge act';
  return h('span', {class: cls}, h('i', {class: 'dot'}), label);
}
function kvrows(rows) {
  return h('div', {class: 'kv'}, rows.map(([k, v, quiet]) => h('div', {class: 'row'}, h('span', {class: 'k'}, k),
    h('span', {class: 'v ell' + (quiet ? ' sub' : ''), title: typeof v === 'string' ? v : null}, v))));
}
function panel(title, ...kids) { return h('section', {class: 'panel'}, h('h3', null, title), ...kids); }
function filterParams() {
  const {p} = parse();
  return {lane: p.get('lane') === 'all' ? '' : p.get('lane') || '', theme: p.get('theme') || ''};
}
const isErr = n => /^Error at/.test(n);
const needIcon = n => isErr(n) ? 'bad' : 'act';

function stageBar(d) {
  const idx = d.status === 'changes' ? 5 : d.status === 'rejected' ? 3 : STAGES.findIndex(s => s[0] === d.status);
  const closed = d.status === 'done' || d.status === 'rejected';
  const late = !closed && hoursSince(d.updated) > STUCK_HOURS;
  const bars = STAGES.map(([k, label], i) => {
    let c = 'na';
    if (d.status === 'done') c = 'done';
    else if (i < idx) c = 'done';
    else if (i === idx) c = d.status === 'rejected' ? 'done' : late ? 'late' : 'cur';
    else if (d.status === 'rejected') c = 'na';
    else c = '';
    return h('i', {class: c, title: label});
  });
  const labels = STAGES.map(([k, label], i) => h('span', {class: i === idx && !closed ? 'cur' : '', title: label}, label));
  return h('div', {class: 'stagebar', role: 'img', 'aria-label': 'Stage: ' + (STATUS_LABEL[d.status] || d.status)},
    h('div', {class: 'bars'}, bars), h('div', {class: 'labels'}, labels));
}

function logLine(h0) {
  const verbs = {'new>transcribing': 'Read the files', 'transcribing>detecting': 'Got the transcript', 'detecting>proposed': 'Picked a theme',
    'proposed>approved': 'Approved the reel', 'proposed>rejected': 'Rejected the reel', 'approved>editing': 'Wrote the edit brief',
    'editing>in_review': 'Sent to review', 'in_review>done': 'Finished the reel', 'in_review>changes': 'Asked for changes', 'changes>editing': 'Restarted the edit'};
  const what = !h0.from ? 'Found in the inbox' : verbs[h0.from + '>' + h0.to] || 'Moved to ' + (STATUS_LABEL[h0.to] || h0.to);
  return {when: when(h0.at), what, why: h0.why || ''};
}
function activityLog(history) {
  const lines = [];
  for (const x of history.map(logLine)) {  // back-to-back repeats fold into one row with a count
    const last = lines[lines.length - 1];
    if (last && last.what === x.what && last.why === x.why) last.n++; else lines.push({...x, n: 1});
  }
  return h('div', {class: 'log'}, lines.reverse().map(l => h('div', {class: 'tr', title: `${l.what}: ${l.why}`},
    h('span', {class: 'when'}, l.when), h('span', {class: 'ell name'}, l.what, l.n > 1 ? h('span', {class: 'fold'}, '×' + l.n) : null),
    h('span', {class: 'ell why'}, l.why))));
}

/* ---------- actions ---------- */
async function act(btn, path, body, okTitle) {
  btn.classList.add('busy');
  try {
    const r = await api(path, body);
    toast('success', okTitle || 'Done', r.message);
    return true;
  } catch (e) {
    toast('error', "That didn't work", e.message);
    return false;
  } finally { btn.classList.remove('busy'); }
}
function rejectDialog(d) {
  const ta = h('textarea', {id: 'why', maxlength: '2000', placeholder: 'For example: wrong theme, this is a podcast clip'});
  const msg = h('div', {class: 'msg'}, 'Up to 2,000 characters. The editor learns from this.');
  const field = h('div', {class: 'field'}, h('label', {for: 'why'}, 'Why reject it?'), ta, msg);
  ta.addEventListener('input', () => { field.classList.remove('bad'); msg.textContent = 'Up to 2,000 characters. The editor learns from this.'; });
  const ok = h('button', {class: 'btn danger', type: 'submit'}, 'Reject reel');
  const f = h('form', {novalidate: true, onsubmit: async e => {
    e.preventDefault();
    if (!ta.value.trim()) { field.classList.add('bad'); msg.textContent = 'Say why before rejecting.'; ta.focus(); return; }
    if (await act(ok, '/api/decide', {id: d.id, decision: 'reject', comment: ta.value}, 'Reel rejected')) { closeDialog(); render(); }
  }}, h('h2', null, 'Reject ' + d.name + '?'), h('p', null, 'Nothing will be made from this reel. You can still change your mind until the next step runs.'), field,
  h('div', {class: 'foot'}, h('button', {class: 'btn text', type: 'button', onclick: closeDialog}, 'Cancel'), ok));
  openDialog(f);
}
function resultDialog(d) {
  let pick = '';
  const ta = h('textarea', {id: 'cm', maxlength: '2000', placeholder: 'For example: captions cut the last word of answer 2'});
  const msg = h('div', {class: 'msg'}, 'Required when you ask for changes.');
  const field = h('div', {class: 'field'}, h('label', {for: 'cm'}, 'Comment'), ta, msg);
  const ok = h('button', {class: 'btn primary', type: 'submit', disabled: true}, 'Record result');
  const why = h('span', {class: 'hint'}, 'Pick a result first.');
  const opts = [['approved', 'Approved'], ['changes', 'Changes']].map(([v, l]) => h('button', {type: 'button', role: 'radio', 'aria-checked': 'false', onclick: ev => {
    pick = v; opts.forEach(b => b.setAttribute('aria-checked', String(b === ev.currentTarget))); ok.disabled = false; why.textContent = '';
  }}, ic('check'), l));
  const f = h('form', {novalidate: true, onsubmit: async e => {
    e.preventDefault();
    if (pick === 'changes' && !ta.value.trim()) { field.classList.add('bad'); msg.textContent = 'Say what must change.'; ta.focus(); return; }
    if (await act(ok, '/api/review-result', {id: d.id, result: pick, comment: ta.value}, 'Result recorded')) { closeDialog(); render(); }
  }}, h('h2', null, 'Record the review of ' + d.name), h('p', null, 'The next step moves the reel on: finished if approved, back to the editor if it needs changes.'),
  h('div', {class: 'choice', role: 'radiogroup', 'aria-label': 'Review result'}, opts), field,
  h('div', {class: 'foot'}, why, h('button', {class: 'btn text', type: 'button', onclick: closeDialog}, 'Cancel'), ok));
  ta.addEventListener('input', () => { field.classList.remove('bad'); msg.textContent = 'Required when you ask for changes.'; });
  openDialog(f);
}

/* ---------- reels: list + detail ---------- */
function recordView(d, tab) {
  const base = '/reels/' + encodeURIComponent(d.id);
  const keep = {...filterParams()};
  const stuck = !['done', 'rejected'].includes(d.status) && hoursSince(d.updated) > STUCK_HOURS;
  const acts = [];
  if (d.awaiting_you) {
    const approve = h('button', {class: 'btn primary', type: 'button', onclick: async e => { if (await act(e.currentTarget, '/api/decide', {id: d.id, decision: 'approve', comment: ''}, 'Reel approved')) render(); }}, 'Approve reel');
    acts.push(h('button', {class: 'btn', type: 'button', onclick: () => rejectDialog(d)}, 'Reject reel'), approve);
  } else if (d.status === 'in_review') {
    acts.push(h('button', {class: 'btn primary', type: 'button', onclick: () => resultDialog(d)}, 'Record result'));
  }
  const line = d.decided ? `Decision saved: ${d.decided}. The next step picks it up.` : d.next + (stuck ? ` Stuck for ${Math.floor(hoursSince(d.updated))} hours.` : '');
  const tabs = [['overview', 'Overview', 0], ['outputs', 'Outputs', d.outputs.length], ['review', 'Review', d.review.comments.length], ['history', 'History', d.history.length]];
  const kpi = [['Status', STATUS_LABEL[d.status] || d.status], ['Theme', d.theme_label || 'Not set'], ['Sure', d.theme ? pct(d.confidence) : '-'],
    ['Length', d.proposal.target_seconds ? '~' + d.proposal.target_seconds + ' s' : '-']];
  const rec = h('article', {class: 'card rec', 'aria-label': 'Reel ' + d.name},
    h('div', {class: 'r1'}, h('span', {class: 'idchip ell', title: d.id}, d.id), h('span', {class: 'hint ell hidephone'}, d.theme_label),
      h('a', {class: 'iconbtn x', href: href('/', keep), 'aria-label': 'Close record', title: 'Close (Esc)'}, ic('x'))),
    h('div', {class: 'r2'}, h('div', {class: 't'}, h('h2', {class: 'ell', title: d.name}, d.name), h('p', {class: 'hint'}, line)),
      acts.length ? h('div', {class: 'acts'}, acts) : null),
    stageBar(d),
    h('div', {class: 'kpi'}, kpi.map(([k, v]) => h('div', null, h('span', {class: 'eyebrow'}, k), h('span', {class: 'v ell', title: v}, v)))),
    h('nav', {class: 'utabs', 'aria-label': 'Record sections'}, tabs.map(([k, l, n]) => h('a', {href: href(base, {...keep, tab: k === 'overview' ? '' : k}), 'aria-current': String(tab === k)}, l, n ? h('span', {class: 'n'}, n) : null))),
    recordBody(d, tab));
  return rec;
}
function recordBody(d, tab) {
  if (tab === 'outputs') {
    return h('div', {class: 'body'}, d.outputs.length ? panel('Finished files', kvrows(d.outputs.map((o, i) => [String(i + 1), o]))) : h('div', {class: 'nonebox'}, 'No finished files yet. The Editor records them when the render ends.'));
  }
  if (tab === 'review') {
    return h('div', {class: 'body'}, d.review.comments.length ? panel('Reviewer comments', h('ul', {class: 'list'}, d.review.comments.map(c => h('li', null, ic('info'), h('span', null, c)))))
      : h('div', {class: 'nonebox'}, d.status === 'in_review' ? 'No comments yet. Record the result with the button above.' : 'No review comments. They appear when the reviewer answers.'));
  }
  if (tab === 'history') return activityLog(d.history);
  const needs = d.needs.map(n => h('li', {class: needIcon(n)}, ic(isErr(n) ? 'alert' : 'info'), h('span', null, n)));
  if (d.decided) needs.unshift(h('li', {class: 'act'}, ic('check'), h('span', null, `Decision saved: ${d.decided}.`)));
  const nextItems = needs.length ? needs : [h('li', null, ic('check'), h('span', null, 'Nothing needs you on this reel.'))];
  const n = d.note, p = d.proposal, ap = d.approval_detail;
  const left = h('div', {class: 'col'},
    h('section', {class: 'panel next'}, h('h3', null, 'Next step'), h('p', {class: 'sect'}, d.next), h('ul', {class: 'list'}, nextItems)),
    panel('Who', kvrows([['Name', n.name || 'Missing', !n.name], ['Team', n.team || '-'], ['Result', n.result || '-'], ['Handle', n.handle || '-']])),
    panel('Proposal', kvrows([['Hook', p.hook || '-'], ['Length', p.target_seconds ? 'about ' + p.target_seconds + ' s' : '-'], ['Music', p.music || '-'],
      ['Inserts', p.inserts.length ? p.inserts.join(', ') : 'None']])),
    panel('Why this theme', d.evidence.length ? h('ul', {class: 'list'}, d.evidence.map(e => h('li', null, ic('check'), h('span', null, e)))) : h('div', {class: 'nonebox'}, 'No evidence recorded yet.')));
  const right = h('div', {class: 'col'},
    panel('Footage', d.files.length ? kvrows(d.files.map(f => [f.kind || 'file', f.name + (f.seconds ? ' · ' + Math.round(f.seconds) + ' s' : '')])) : h('div', {class: 'nonebox'}, 'No files found.')),
    panel('Approval', kvrows([['State', ap.state === 'none' ? 'Not asked yet' : ap.state], ['By', ap.by || '-'], ['At', ap.at ? when(ap.at) : '-'], ['Comment', ap.comment || '-']])),
    panel('Transcript', kvrows([['Source', d.transcript.source || '-'], ['Trust', d.transcript.trust || '-']])));
  return h('div', {class: 'body'}, left, right);
}

function laneOf(r) { return (LANES.find(l => l[2] && l[2].includes(r.status)) || [])[0]; }
function listRows(reels, selId, compact, keep) {
  compact = compact || matchMedia('(max-width:719px)').matches;
  const rows = reels.map(r => {
    const u = href('/reels/' + encodeURIComponent(r.id), keep);
    if (compact) return h('a', {class: 'tr', href: u, 'aria-current': String(r.id === selId)},
      h('span', {class: 'name ell', title: r.name}, r.name), h('span', {class: 'l2'}, badge(r), h('span', {class: 'sub ell'}, [r.theme_label, r.theme ? pct(r.confidence) : ''].filter(Boolean).join(' · '))));
    const err = r.needs.some(isErr);
    return h('a', {class: 'tr cols-full', href: u, 'aria-current': String(r.id === selId)},
      h('span', {class: 'name ell', title: r.name}, r.name), h('span', null, badge(r)),
      h('span', {class: 'ell sub', title: r.theme_label}, r.theme_label || '-'), h('span', {class: 'num'}, r.theme ? pct(r.confidence) : '-'),
      h('span', {class: 'sub ell'}, ago(r.updated)),
      r.needs.length ? h('span', {class: err ? 'errc' : 'sub', title: r.needs.join('\n')}, h('span', {class: 'sr'}, r.needs.length + ' needs'), ic(err ? 'alert' : 'info')) : h('span'));
  });
  const th = compact ? null : h('div', {class: 'tr th cols-full'}, h('span', null, 'Reel'), h('span', null, 'Status'), h('span', null, 'Theme'), h('span', {class: 'num'}, 'Sure'), h('span', null, 'Updated'), h('span'));
  return h('div', {class: 'card table' + (compact ? ' compact' : '')}, th, rows);
}

async function pageReels({id, p}) {
  const tab = p.get('tab') || 'overview';
  const res = await guarded(async sig => {
    const [reels, detail] = await Promise.all([api('/api/reels', undefined, sig),
      id ? api('/api/reels/' + encodeURIComponent(id), undefined, sig).catch(e => { if (e.status === 404 || e.status === 400) return {missing: e.message}; throw e; }) : null]);
    return {reels, detail};
  }, 'table');
  if (!res) return;
  const {reels, detail} = res.data;
  setCount(reels);
  const lane = p.get('lane') || 'all', theme = p.get('theme') || '';
  const keep = {lane: lane === 'all' ? '' : lane, theme};
  const waiting = reels.filter(r => r.awaiting_you).length;
  const inLane = r => lane === 'all' || laneOf(r) === lane;
  const shown = reels.filter(r => inLane(r) && (!theme || r.theme === theme));
  const sub = reels.length ? `${reels.length} ${reels.length === 1 ? 'reel' : 'reels'} · ${waiting} waiting for your yes` : 'No reels yet';
  const themes = [...new Map(reels.filter(r => r.theme).map(r => [r.theme, r.theme_label])).entries()];
  const rec = detail && !detail.missing ? detail : null;
  document.title = (rec ? rec.name + ' · ' : '') + 'Reels · Editing factory';
  crumb.replaceChildren(...[h('span', null, 'Reels'), rec ? h('span', null, '/') : null, rec ? h('b', {class: 'ell'}, rec.name) : null].filter(Boolean));

  const out = [head('Reels', sub)];
  if (!reels.length) {
    out.push(stateBox('empty', 'No reels yet', 'Drop a folder of footage into the inbox, then run one step. The factory will pick it up.', 'Run one step', () => document.getElementById('tick').click()));
    return show(out);
  }
  const open0 = !!(rec || (detail && detail.missing));
  out.push(h('nav', {class: 'tabs' + (open0 ? ' hidephone' : ''), 'aria-label': 'Status'}, LANES.map(([k, label, sts]) => {
    const n = reels.filter(r => (k === 'all' || laneOf(r) === k) && (!theme || r.theme === theme)).length;
    return h('a', {href: href('/', {lane: k === 'all' ? '' : k, theme}), 'aria-current': String(lane === k)}, label, h('span', {class: 'n'}, n));
  })));
  if (themes.length) {
    out.push(h('div', {class: 'filters' + (open0 ? ' hidephone' : ''), role: 'group', 'aria-label': 'Theme filter'}, h('span', {class: 'eyebrow lbl'}, 'Theme'),
      h('a', {class: 'pill', href: href('/', {lane: keep.lane}), 'aria-pressed': String(!theme)}, 'All themes'),
      themes.map(([k, l]) => h('a', {class: 'pill', href: href(rec ? '/reels/' + encodeURIComponent(rec.id) : '/', {lane: keep.lane, theme: theme === k ? '' : k, tab: rec && tab !== 'overview' ? tab : ''}), 'aria-pressed': String(theme === k)}, l))));
  }
  let list;
  if (!shown.length) {
    list = stateBox('empty', 'No reels match', 'Nothing fits this status and theme. Your reels are still here.', 'Clear filters', () => go('/'));
  } else list = listRows(shown, rec ? rec.id : '', !!(rec || (detail && detail.missing)), keep);
  const open = rec || (detail && detail.missing);
  const cols = h('div', {class: 'cols'}, h('div', {class: 'listcol ' + (open ? 's4 hidephone' : 's12')}, list));
  if (rec) cols.append(h('div', {class: 'recwrap s8'}, recordView(rec, tab)));
  else if (detail && detail.missing) cols.append(h('div', {class: 'recwrap s8'}, stateBox('err', "That reel isn't here", 'It may have been moved or removed. The rest of your reels are untouched.', 'Back to reels', () => go(href('/', keep)))));
  out.push(cols);
  show(out);
}

/* ---------- daily review ---------- */
const REVIEW_EMPTY = {Failing: 'Nothing failing.', Working: 'No moves today.', 'Needs you': 'Nothing needs you.', 'Added and updated': 'Nothing new in git today.', Tomorrow: 'Nothing queued.'};
function reviewRow(text) {
  text = text.replace(/ -> /g, ' to ').replace(/\bin_review\b/g, 'in review');
  let m = text.match(/^([0-9a-f]{7,}) (.*)$/);
  if (m) return h('div', {class: 'rrow', title: text}, h('span', {class: 'h'}, m[1]), h('span', {class: 'm ell'}, m[2]));
  m = text.match(/^(.+?): (.*)$/);
  if (m) return h('div', {class: 'rrow', title: text}, h('span', {class: 's ell'}, m[1]), h('span', {class: 'm ell'}, m[2]));
  return h('div', {class: 'rrow', title: text}, h('span', {class: 'm ell'}, text));
}
async function pageReview() {
  const res = await guarded(sig => api('/api/review', undefined, sig), 'review');
  if (!res) return;
  const d = res.data;
  document.title = 'Daily review · Editing factory';
  crumb.replaceChildren(h('b', null, 'Daily review'));
  const span = {Failing: 's6', Working: 's6', 'Needs you': 's6', Tomorrow: 's6', 'Added and updated': 's12'};
  const order = ['Failing', 'Working', 'Needs you', 'Tomorrow', 'Added and updated'];
  const tiles = [...d.sections].sort((a, b) => order.indexOf(a.title) - order.indexOf(b.title)).map(s => h('section', {class: 'card tile ' + (span[s.title] || 's6')},
    h('div', {class: 'hd'}, h('h3', null, s.title), ic(s.title === 'Failing' ? 'alert' : s.title === 'Needs you' ? 'info' : 'check')),
    s.empty ? h('div', {class: 'nonebox'}, REVIEW_EMPTY[s.title] || 'Nothing today.') : null,
    s.items.map(reviewRow), s.groups.map(g => [h('div', {class: 'eyebrow grouplbl'}, g.title), g.items.map(reviewRow)])));
  const dm = d.title.match(/(\d{4})-(\d{2})-(\d{2})/);
  const day = dm ? new Date(+dm[1], +dm[2] - 1, +dm[3]).toLocaleDateString('en-GB', {day: 'numeric', month: 'short', year: 'numeric', weekday: 'short'}) : '';
  show([head('Daily review', day + ' · ' + d.summary), h('div', {class: 'bento'}, tiles)]);
}

/* ---------- agents ---------- */
async function pageAgents() {
  const res = await guarded(sig => api('/api/agents', undefined, sig), 'cards');
  if (!res) return;
  const agents = res.data;
  document.title = 'Agents · Editing factory';
  crumb.replaceChildren(h('b', null, 'Agents'));
  if (!agents.length) return show([head('Agents', ''), stateBox('empty', 'No agent cards found', 'The cards live in factory/agents. Restore that folder from git.', null)]);
  const busy = agents.reduce((n, a) => n + a.acting_on.length, 0);
  const chips = list => h('div', {class: 'chiplist'}, list.map(r => h('a', {class: 'chipl', href: '/reels/' + encodeURIComponent(r.id), title: r.name}, h('span', {class: 'ell'}, r.name))));
  const tiles = agents.map(a => h('section', {class: 'card tile s4'},
    h('div', {class: 'hd'}, h('h3', null, a.name), ic('agents')),
    h('p', {class: 'job', title: a.does || a.job}, a.job),
    kvrows([['Reads', a.reads], ['Writes', a.writes], ['Hands to', a.hands_to]]),
    h('div', {class: 'now'}, h('span', {class: 'eyebrow'}, 'Now'),
      !a.built ? h('span', {class: 'badge quiet'}, h('i', {class: 'dot'}), 'Not built yet')
        : a.acting_on.length ? chips(a.acting_on) : a.waiting_on_you.length ? null : h('span', {class: 'sub'}, 'Idle'),
      a.waiting_on_you.length ? [h('span', {class: 'sub'}, 'Waiting for your yes'), chips(a.waiting_on_you)] : null),
    a.must.length || a.never.length ? h('details', {class: 'more'}, h('summary', null, `Rules (${a.must.length + a.never.length})`),
      h('ul', null, a.must.map(x => h('li', null, 'Must: ' + x)), a.never.map(x => h('li', null, 'Never: ' + x)))) : null));
  show([head('Agents', `${agents.filter(a => a.built).length} roles at work · ${busy} ${busy === 1 ? 'reel' : 'reels'} in their hands`), h('div', {class: 'bento'}, tiles)]);
}

/* ---------- themes (read-only) ---------- */
async function pageThemes({p}) {
  const res = await guarded(sig => api('/api/themes', undefined, sig), 'table');
  if (!res) return;
  const themes = res.data;
  document.title = 'Themes · Editing factory';
  crumb.replaceChildren(h('b', null, 'Themes'));
  if (!themes.length) return show([head('Themes', 'Read-only'), stateBox('empty', 'No themes found', 'The keyword table is factory/themes.json. Restore it from git.', null)]);
  const sel = themes.find(t => t.key === p.get('t')) || themes[0];
  const list = h('div', {class: 'card table compact'}, themes.map(t => h('a', {class: 'tr', href: href('/themes', {t: t.key}), 'aria-current': String(t.key === sel.key)},
    h('span', {class: 'name ell', title: t.label}, t.label), h('span', {class: 'l2'}, h('span', {class: 'badge quiet'}, h('i', {class: 'dot'}), t.status || '-'), h('span', {class: 'sub ell mono'}, t.key)))));
  const f = sel.footage || {};
  const secs = (sel.default_seconds || []).join('-');
  const kw = [...sel.keywords].sort((a, b) => b.weight - a.weight);
  const rec = h('article', {class: 'card rec'},
    h('div', {class: 'r1'}, h('span', {class: 'idchip ell'}, sel.key), h('span', {class: 'hint'}, 'Read-only')),
    h('div', {class: 'r2'}, h('div', {class: 't'}, h('h2', {class: 'ell', title: sel.label}, sel.label), h('p', {class: 'hint ell', title: sel.card}, sel.card))),
    h('div', {class: 'kpi'}, [['Status', sel.status || '-'], ['Length', secs ? secs + ' s' : '-'], ['Keywords', String(sel.keywords.length)], ['Questions', String(sel.questions.length)]]
      .map(([k, v]) => h('div', null, h('span', {class: 'eyebrow'}, k), h('span', {class: 'v ell'}, v)))),
    h('div', {class: 'body'},
      h('div', {class: 'col'}, panel('Keywords', kw.length ? h('div', {class: 'chiplist'}, kw.map(k => h('span', {class: 'badge', title: 'Weight ' + k.weight}, k.term, h('span', {class: 'mono sub'}, k.weight)))) : h('div', {class: 'nonebox'}, 'No keywords.')),
        panel('Questions it listens for', sel.questions.length ? h('ul', {class: 'list'}, sel.questions.map(q => h('li', null, ic('info'), h('span', null, q)))) : h('div', {class: 'nonebox'}, 'No question phrases.'))),
      h('div', {class: 'col'}, panel('Footage signals', kvrows([['Videos', f.videos ? f.videos.join('-') : '-'], ['Orientation', f.orientation || '-'], ['Seconds', f.seconds ? f.seconds.join('-') : '-'],
        ['Screen rec.', f.screen_recording === undefined ? '-' : f.screen_recording ? 'Yes' : 'No']])))));
  show([head('Themes', 'Read-only. Edit factory/themes.json in git to change a theme.'), h('div', {class: 'cols'}, h('div', {class: 's4'}, list), h('div', {class: 's8 recwrap'}, rec))]);
}

/* ---------- assets ---------- */
async function pageAssets() {
  const res = await guarded(sig => api('/api/assets', undefined, sig), 'table');
  if (!res) return;
  const {items, missing} = res.data;
  document.title = 'Assets · Editing factory';
  crumb.replaceChildren(h('b', null, 'Assets'));
  if (missing || !items.length) return show([head('Assets', ''), stateBox('empty', 'No assets listed', 'The list is assets/MANIFEST.json. Add a track with its licence and credit line, then fetch it.', null)]);
  const left = items.filter(a => !a.fetched).length;
  const out = [head('Assets', `${items.length} files · ${items.length - left} downloaded`)];
  if (left) out.push(h('div', {class: 'inl', role: 'note'}, ic('info'), h('div', null, h('b', {class: 'name'}, `${left} ${left === 1 ? 'file is' : 'files are'} not downloaded yet`), h('div', {class: 'sub mono'}, 'python3 assets/fetch_assets.py'))));
  const copy = a => async () => { try { await navigator.clipboard.writeText(a.credit); toast('success', 'Credit line copied', a.title); } catch (e) { toast('error', "Couldn't copy", 'Select the line and copy it by hand.'); } };
  out.push(h('div', {class: 'card table'},
    h('div', {class: 'tr th cols-asset'}, h('span', null, 'Title'), h('span', null, 'Kind'), h('span', null, 'Licence'), h('span', null, 'Credit line'), h('span', {class: 'num'}, 'BPM'), h('span', null, 'File'), h('span')),
    items.map(a => h('div', {class: 'tr cols-asset'},
      h('span', {class: 'ell'}, h('div', {class: 'name ell', title: a.title}, a.title), h('div', {class: 'sub ell', title: a.artist}, a.artist)),
      h('span', {class: 'sub hidephone'}, a.kind), h('span', {class: 'sub ell', title: a.licence}, a.licence || '-'),
      h('span', {class: 'sub ell', title: a.credit}, a.credit || 'Missing'), h('span', {class: 'num hidephone'}, a.bpm || '-'),
      h('span', null, h('span', {class: a.fetched ? 'badge quiet' : 'badge act'}, h('i', {class: 'dot'}), a.fetched ? 'Downloaded' : 'Not downloaded')),
      a.credit ? h('button', {class: 'iconbtn', type: 'button', 'aria-label': 'Copy credit line for ' + a.title, title: 'Copy credit line', onclick: copy(a)}, ic('copy')) : h('span')))));
  show(out);
}

/* ---------- shell ---------- */
function show(nodes) {
  const first = view.dataset.sec !== parse().sec;
  view.dataset.sec = parse().sec;
  view.replaceChildren(...nodes.filter(Boolean));
  view.classList.toggle('enter', first);
}
function setCount(reels) {
  const n = reels.filter(r => r.awaiting_you).length;
  const el = document.querySelector('#nav a[data-sec="reels"] .count');
  if (el) { el.textContent = n || ''; el.hidden = !n; }
}
function buildNav() {
  const nav = document.getElementById('nav');
  nav.replaceChildren(...NAV.flatMap(([u, label, icon, grp]) => [
    grp ? h('span', {class: 'eyebrow grp'}, grp) : null,
    h('a', {href: u, 'data-sec': icon, title: label}, ic(icon), h('span', {class: 'lbl'}, label), icon === 'reels' ? h('span', {class: 'count', hidden: true}) : null)]).filter(Boolean));
}
function markNav() {
  const {sec} = parse();
  document.querySelectorAll('#nav a').forEach(a => { if (a.dataset.sec === sec) a.setAttribute('aria-current', 'page'); else a.removeAttribute('aria-current'); });
}
const PAGES = {reels: pageReels, review: pageReview, agents: pageAgents, themes: pageThemes, assets: pageAssets};
function render() {
  const route = parse();
  markNav();
  const fn = PAGES[route.sec];
  if (!fn) { show([head('Page not found', ''), stateBox('empty', "That page isn't here", 'Use the menu to go to a page that exists.', 'Go to reels', () => go('/'))]); return; }
  fn(route);
  if (route.sec !== 'reels') api('/api/reels').then(setCount).catch(() => {});
}

/* appearance: System / Dark / Light, neutral like navigation, 200 ms colour cross-fade */
function appearance() {
  const KEY = 'factory-appearance';
  let cur = 'system';
  try { cur = localStorage.getItem(KEY) || 'system'; } catch (e) { /* storage may be blocked */ }
  const apply = v => {
    document.documentElement.classList.add('theme-fade');
    if (v === 'system') document.documentElement.removeAttribute('data-theme'); else document.documentElement.dataset.theme = v;
    setTimeout(() => document.documentElement.classList.remove('theme-fade'), 220);
    document.querySelectorAll('#appear button').forEach(b => b.setAttribute('aria-pressed', String(b.dataset.v === v)));
    try { localStorage.setItem(KEY, v); } catch (e) { /* ignore */ }
  };
  const box = document.getElementById('appear');
  box.replaceChildren(...[['system', 'System', 'monitor'], ['dark', 'Dark', 'moon'], ['light', 'Light', 'sun']].map(([v, l, i]) =>
    h('button', {type: 'button', 'data-v': v, 'aria-pressed': 'false', title: l, 'aria-label': l, onclick: () => apply(v)}, ic(i), h('span', {class: 'lbl'}, l))));
  apply(cur);
}

document.getElementById('tick').addEventListener('click', async e => {
  const btn = e.currentTarget;
  btn.classList.add('busy');
  try {
    const r = await api('/api/tick', {});
    if (r.log.length) toast('success', r.log.length === 1 ? 'One reel moved' : r.log.length + ' changes', r.log.slice(0, 2).join('; ') + (r.log.length > 2 ? ` and ${r.log.length - 2} more` : ''));
    else toast('info', 'Nothing changed', 'Every reel is waiting on something else.');
    render();
  } catch (err) { toast('error', "The step didn't run", err.message); } finally { btn.classList.remove('busy'); }
});

buildNav();
appearance();
render();
})();
