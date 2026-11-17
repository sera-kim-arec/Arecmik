/**
 * Arecmik → Google Drive 자동 내보내기
 * 매일 밤 앱 기록(WORK)을 '업무 히스토리 / 앱 기록 (자동)' 폴더에 구글 문서로 정리해요.
 * LIFE(일기·글·컬렉션)는 내보내지 않아요.
 *
 * 처음 한 번: setup() 실행 → 권한 허용. 이후엔 매일 23시쯤 자동 실행.
 */
const PROJECT = 'arecmik-25699';
const NS = 'arecmik2';
const FOLDER_ID = '1ud6_JdKy9tj9Zt6qNQCaXOmW6Y5QX16k'; // 업무 히스토리 / 앱 기록 (자동)
const TZ = 'Asia/Seoul';

function setup() {
  ScriptApp.getProjectTriggers().forEach(t => { if (t.getHandlerFunction() === 'exportAll') ScriptApp.deleteTrigger(t); });
  ScriptApp.newTrigger('exportAll').timeBased().everyDays(1).atHour(23).inTimezone(TZ).create();
  exportAll();
}

function exportAll() {
  const S = loadState();
  const docs = buildDocs(S, new Date());
  const props = PropertiesService.getScriptProperties();
  const idx = JSON.parse(props.getProperty('INDEX') || '{}');
  let made = 0, updated = 0, same = 0;
  docs.forEach(d => {
    const h = hash(d.html); const cur = idx[d.name];
    if (cur && cur.h === h && fileAlive(cur.id)) { same++; return; }
    if (cur && fileAlive(cur.id)) { if (updateDoc(cur.id, d.html)) { idx[d.name] = { id: cur.id, h }; updated++; return; } trash(cur.id); }
    const id = createDoc(d.name, d.html); idx[d.name] = { id, h }; made++;
  });
  // 더 이상 없는 문서(예: 지운 카테고리)는 휴지통으로
  const names = new Set(docs.map(d => d.name));
  Object.keys(idx).forEach(n => { if (!names.has(n)) { trash(idx[n].id); delete idx[n]; } });
  props.setProperty('INDEX', JSON.stringify(idx));
  console.log(`문서 ${docs.length}개 · 새로 ${made} · 고침 ${updated} · 그대로 ${same}`);
}

/* ---------- Firestore ---------- */
function fsGet(path, query) {
  const url = `https://firestore.googleapis.com/v1/projects/${PROJECT}/databases/(default)/documents/${path}${query ? '?' + query : ''}`;
  const r = UrlFetchApp.fetch(url, { headers: { Authorization: 'Bearer ' + ScriptApp.getOAuthToken(), 'X-Goog-User-Project': PROJECT }, muteHttpExceptions: true });
  if (r.getResponseCode() !== 200) throw new Error(`Firestore ${r.getResponseCode()}: ${r.getContentText().slice(0, 400)}`);
  return JSON.parse(r.getContentText());
}
function findUid() {
  const p = PropertiesService.getScriptProperties().getProperty('UID'); if (p) return p;
  const r = fsGet('users', 'showMissing=true&pageSize=50');
  const ids = (r.documents || []).map(d => d.name.split('/').pop());
  if (ids.length !== 1) throw new Error(`앱 사용자 ID를 ${ids.length}개 찾았어요. 프로젝트 설정 › 스크립트 속성에 UID를 직접 넣어 주세요: ${ids.join(', ')}`);
  PropertiesService.getScriptProperties().setProperty('UID', ids[0]);
  return ids[0];
}
function loadState() {
  const uid = findUid(); const S = { items: [], projects: [], folders: [], docs: [], routines: [], retros: [], rmonths: [], memo: [], weekNotes: {}, settings: {} };
  let tok = '';
  do {
    const r = fsGet(`users/${uid}/${NS}`, 'pageSize=300' + (tok ? '&pageToken=' + encodeURIComponent(tok) : ''));
    (r.documents || []).forEach(d => {
      const key = d.name.split('/').pop(); const j = d.fields && d.fields.j && d.fields.j.stringValue; if (!j) return;
      let v; try { v = JSON.parse(j); } catch (e) { return; }
      const [col] = key.split('__');
      if (key === 'meta__memo') S.memo = v.memo || [];
      else if (key === 'meta__weeks') S.weekNotes = v.weeks || {};
      else if (key === 'meta__settings') S.settings = v.settings || {};
      else if (S[col] && Array.isArray(S[col])) S[col].push(v);
    });
    tok = r.nextPageToken || '';
  } while (tok);
  return S;
}

/* ---------- Drive (REST, 구글 문서로 변환) ---------- */
function driveFetch(url, opt) { opt = opt || {}; opt.headers = Object.assign({ Authorization: 'Bearer ' + ScriptApp.getOAuthToken() }, opt.headers || {}); opt.muteHttpExceptions = true; return UrlFetchApp.fetch(url, opt); }
function createDoc(name, html) {
  const b = 'arecmik' + Date.now();
  const meta = JSON.stringify({ name, mimeType: 'application/vnd.google-apps.document', parents: [FOLDER_ID] });
  const body = `--${b}\r\nContent-Type: application/json; charset=UTF-8\r\n\r\n${meta}\r\n--${b}\r\nContent-Type: text/html; charset=UTF-8\r\n\r\n${html}\r\n--${b}--`;
  const r = driveFetch('https://www.googleapis.com/upload/drive/v3/files?uploadType=multipart&fields=id', { method: 'post', contentType: `multipart/related; boundary=${b}`, payload: Utilities.newBlob(body).getBytes() });
  if (r.getResponseCode() !== 200) throw new Error(`문서 만들기 실패 ${r.getResponseCode()}: ${r.getContentText().slice(0, 300)}`);
  return JSON.parse(r.getContentText()).id;
}
function updateDoc(id, html) {
  const r = driveFetch(`https://www.googleapis.com/upload/drive/v3/files/${id}?uploadType=media`, { method: 'patch', contentType: 'text/html; charset=UTF-8', payload: Utilities.newBlob(html, 'text/html').getBytes() });
  return r.getResponseCode() === 200;
}
function fileAlive(id) { try { return !DriveApp.getFileById(id).isTrashed(); } catch (e) { return false; } }
function trash(id) { try { DriveApp.getFileById(id).setTrashed(true); } catch (e) { } }
function hash(s) { return Utilities.base64Encode(Utilities.computeDigest(Utilities.DigestAlgorithm.MD5, s, Utilities.Charset.UTF_8)); }

/* ---------- 문서 만들기 (순수 함수) ---------- */
function buildDocs(S, now) {
  const esc = t => String(t == null ? '' : t).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  const inl = t => esc(String(t || '').replace(/​/g, ''))
    .replace(/`([^`\n]+)`(\{[roygbpk]\})?/g, '<code>$1</code>')
    .replace(/\*\*([^*\n]+)\*\*/g, '<b>$1</b>').replace(/~~([^~\n]+)~~/g, '<s>$1</s>');
  const WD = ['일', '월', '화', '수', '목', '금', '토'];
  const dlabel = d => { const x = new Date(d + 'T00:00:00'); return `${+d.slice(5, 7)}월 ${+d.slice(8, 10)}일 (${WD[x.getDay()]})`; };
  const short = d => d ? `${+d.slice(5, 7)}/${+d.slice(8, 10)}` : '';
  const hm = ts => { const x = new Date(ts); return ('0' + x.getHours()).slice(-2) + ':' + ('0' + x.getMinutes()).slice(-2); };
  const byId = (arr) => { const m = {}; (arr || []).forEach(x => { m[x.id] = x; }); return m; };
  const items = (S.items || []).filter(i => !i.cancel); const I = byId(items); const P = byId(S.projects); const F = byId(S.folders);
  const has = bl => (bl || []).some(b => (b.text || '').trim() || b.src || b.rows);
  const blocks = bl => { // 블록 → HTML (목록 들여쓰기 유지)
    let h = ''; let open = []; const close = (n) => { while (open.length > n) h += `</${open.pop()}>`; };
    (bl || []).forEach(b => {
      const t = b.type, lvl = (b.indent || 0);
      const listy = t === 'bullet' || t === 'num' || t === 'todo';
      if (listy) {
        const tag = t === 'num' ? 'ol' : 'ul';
        close(lvl + 1); while (open.length < lvl + 1) { h += `<${tag}>`; open.push(tag); }
        h += `<li>${t === 'todo' ? (b.done ? '☑ ' : '☐ ') : ''}${inl(b.text)}</li>`; return;
      }
      close(0);
      if (t === 'divider') h += '<hr>';
      else if (t === 'h') h += `<h4>${inl(b.text)}</h4>`;
      else if (t === 'quote') h += `<blockquote>${inl(b.text)}</blockquote>`;
      else if (t === 'code') h += `<pre>${esc(b.text)}</pre>`;
      else if (t === 'image') h += '<p><i>[사진]</i></p>';
      else if (t === 'link') h += `<p><a href="${esc(b.text)}">${esc(b.text)}</a></p>`;
      else if (t === 'table') h += '<table border="1">' + (b.rows || []).map(r => '<tr>' + r.map(c => `<td>${inl(c)}</td>`).join('') + '</tr>').join('') + '</table>';
      else if ((b.text || '').trim()) h += `<p>${'&nbsp;&nbsp;'.repeat(lvl * 2)}${inl(b.text)}</p>`;
    });
    close(0); return h;
  };
  const logText = c => has(c.blocks) ? blocks(c.blocks) : `<p>${inl(c.text)}</p>`;
  const meta = it => { const p = it.projectId && P[it.projectId]; const par = it.parentId && I[it.parentId];
    return [it.area && `#${esc(it.area)}`, p && `프로젝트 ${inl(p.title)}`, par && `상위: ${inl(par.title)}`].filter(Boolean).join(' · '); };
  const checks = it => (it.checks || []).length ? `<p><b>❗ 꼭 잊지 말 것</b></p><ul>${it.checks.map(c => `<li>${'&nbsp;&nbsp;'.repeat((c.indent || 0) * 2)}${inl(c.text)}</li>`).join('')}</ul>` : '';
  const retroHTML = r => `<li><b>${r.kind === 'feedback' ? '받은 피드백' : '실수'}</b>${r.area ? ` · #${esc(r.area)}` : ''} — ${inl(r.what || '')}${r.next ? `<br>→ 다음엔: ${inl(r.next)}` : ''}</li>`;
  const stamp = `<p><i>Arecmik 앱에서 자동으로 만든 문서예요 · ${Utilities.formatDate(now, TZ, 'yyyy-MM-dd HH:mm')} 기준 · 직접 고치면 다음 내보내기 때 덮어써져요.</i></p>`;
  const page = (title, body) => `<html><head><meta charset="utf-8"></head><body><h1>${esc(title)}</h1>${stamp}${body}</body></html>`;
  const out = [];

  /* 1) 업무일지 — 달별 */
  const days = {}; const day = d => (days[d] = days[d] || { todos: new Set(), done: new Set(), events: new Set(), logs: [], retros: [], memo: null });
  items.forEach(it => {
    if (it.kind === 'event' && it.date) day(it.date).events.add(it.id);
    if (it.kind === 'todo' && it.date) day(it.date).todos.add(it.id);
    if (it.done && it.doneAt) { const d = Utilities.formatDate(new Date(it.doneAt), TZ, 'yyyy-MM-dd'); day(d).done.add(it.id); }
    (it.log || []).forEach(c => { if (c.date) day(c.date).logs.push({ it, c }); });
  });
  (S.retros || []).forEach(r => { if (r.date && (r.what || r.next)) day(r.date).retros.push(r); });
  (S.rmonths || []).forEach(m => { const g = /^j-(\d{4}-\d{2}-\d{2})$/.exec(m.id); if (g && has(m.blocks)) day(g[1]).memo = m.blocks; });
  const months = {}; Object.keys(days).sort().forEach(d => { (months[d.slice(0, 7)] = months[d.slice(0, 7)] || []).push(d); });
  Object.keys(months).forEach(ym => {
    let h = '';
    const mn = (S.rmonths || []).find(m => m.id === 'mn-' + ym); if (mn && has(mn.blocks)) h += `<h2>📌 ${+ym.slice(5)}월 메모</h2>${blocks(mn.blocks)}`;
    months[ym].forEach(d => { const D = days[d]; const parts = [];
      const row = (id, extra) => { const it = I[id]; if (!it) return ''; const lg = D.logs.filter(x => x.it.id === id); const m = meta(it);
        return `<li>${it.kind === 'event' ? '📅 ' + (it.start ? esc(it.start) + ' ' : '') : it.done ? '☑ ' : '☐ '}${inl(it.title || '제목 없음')}${m ? ` <i>(${m})</i>` : ''}${extra || ''}${lg.map(x => `<br>💬 ${hm(x.c.ts)}${logText(x.c)}`).join('')}</li>`; };
      const ev = [...D.events]; if (ev.length) parts.push(`<p><b>일정</b></p><ul>${ev.map(id => row(id)).join('')}</ul>`);
      const td = [...new Set([...D.todos, ...D.done])].filter(id => I[id] && I[id].kind === 'todo');
      const moved = [...new Set(D.logs.map(x => x.it.id))].filter(id => !td.includes(id) && !ev.includes(id));
      if (td.length) parts.push(`<p><b>할일</b></p><ul>${td.map(id => row(id, D.done.has(id) && I[id].date !== d ? ` <i>(이 날 완료)</i>` : '')).join('')}</ul>`);
      if (moved.length) parts.push(`<p><b>다른 날로 옮긴 일 · 이 날 코멘트</b></p><ul>${moved.map(id => row(id, ` <i>(→ ${short(I[id].date)})</i>`)).join('')}</ul>`);
      if (D.memo) parts.push(`<p><b>이 날 메모</b></p>${blocks(D.memo)}`);
      if (D.retros.length) parts.push(`<p><b>복기</b></p><ul>${D.retros.map(retroHTML).join('')}</ul>`);
      if (parts.length) h += `<h2>${dlabel(d)}</h2>${parts.join('')}`;
    });
    if (h) out.push({ name: `업무일지 ${ym}`, html: page(`업무일지 · ${ym.slice(0, 4)}년 ${+ym.slice(5)}월`, h) });
  });

  /* 2) 카테고리별 */
  const areas = {}; items.forEach(it => { if (it.area) (areas[it.area] = areas[it.area] || { items: [], retros: [] }).items.push(it); });
  (S.retros || []).forEach(r => { if (r.area && (r.what || r.next)) (areas[r.area] = areas[r.area] || { items: [], retros: [] }).retros.push(r); });
  Object.keys(areas).forEach(a => { const A = areas[a]; let h = '';
    if (A.retros.length) h += `<h2>지난 실수 · 피드백 (${A.retros.length})</h2><ul>${A.retros.sort((x, y) => (y.date || '').localeCompare(x.date || '')).map(r => retroHTML(r).replace('<li>', `<li>${short(r.date)} `)).join('')}</ul>`;
    const its = A.items.sort((x, y) => (y.date || '0').localeCompare(x.date || '0'));
    h += `<h2>할일 · 일정 (${its.length})</h2>`;
    its.forEach(it => { h += `<h3>${it.kind === 'event' ? '📅' : it.done ? '☑' : '☐'} ${inl(it.title || '제목 없음')} <i>${it.date ? short(it.date) : '날짜 없음'}</i></h3>`;
      const m = meta(it); if (m) h += `<p><i>${m}</i></p>`; h += checks(it);
      (it.log || []).slice().sort((x, y) => x.ts - y.ts).forEach(c => { h += `<p>💬 <b>${short(c.date)}</b></p>${logText(c)}`; });
      if (has(it.memo)) h += `<p><b>메모</b></p>${blocks(it.memo)}`; });
    out.push({ name: `카테고리 · ${a}`, html: page(`카테고리 · ${a}`, h) }); });

  /* 3) 프로젝트 */
  (S.projects || []).forEach(p => { let h = `<p>${esc(p.start || '')}${p.end ? ' ~ ' + esc(p.end) : ''}${p.done ? ' · 완료' : ''}</p>`;
    if (has(p.memo)) h += `<h2>메모</h2>${blocks(p.memo)}`;
    const its = items.filter(i => i.projectId === p.id).sort((x, y) => (x.date || '9').localeCompare(y.date || '9'));
    if (its.length) { h += `<h2>할일 · 일정</h2>`; its.forEach(it => { h += `<h3>${it.kind === 'event' ? '📅' : it.done ? '☑' : '☐'} ${inl(it.title || '')} <i>${it.date ? short(it.date) : ''}</i></h3>${checks(it)}`; (it.log || []).forEach(c => { h += `<p>💬 <b>${short(c.date)}</b></p>${logText(c)}`; }); }); }
    const ds = (S.docs || []).filter(d => d.projectId === p.id); if (ds.length) h += `<h2>연결된 노트</h2><ul>${ds.map(d => `<li>${inl(d.title || '제목 없음')}</li>`).join('')}</ul>`;
    out.push({ name: `프로젝트 · ${p.title || '이름 없음'}`, html: page(`프로젝트 · ${p.title || '이름 없음'}`, h) }); });

  /* 4) 노트 — WORK 폴더별로 한 문서 */
  const fpath = id => { const n = []; let f = F[id]; let g = 0; while (f && g++ < 10) { n.unshift(f.name || '폴더'); f = F[f.parent]; } return n.join(' › '); };
  const isLife = id => { let f = F[id]; let g = 0; while (f && g++ < 10) { if (f.space === 'life') return true; f = F[f.parent]; } return false; };
  const groups = {}; (S.docs || []).forEach(d => { if (d.folder && isLife(d.folder)) return; if (!has(d.blocks) && !(d.title || '').trim()) return; const k = d.folder ? fpath(d.folder) : '폴더 없음'; (groups[k] = groups[k] || []).push(d); });
  Object.keys(groups).forEach(k => { let h = ''; groups[k].sort((a, b) => (a.title || '').localeCompare(b.title || '')).forEach(d => { h += `<h2>${inl(d.title || '제목 없음')}</h2>${blocks(d.blocks)}<hr>`; });
    out.push({ name: `노트 · ${k}`, html: page(`노트 · ${k}`, h) }); });

  /* 5) 메모 · 루틴 · 날짜 없는 할일 */
  let h = '';
  if (has(S.memo)) h += `<h2>상시 메모</h2>${blocks(S.memo)}`;
  const rs = (S.routines || []); const FQ = { daily: '매일', weekly: '매주', monthly: '매달', any: '수시' };
  if (rs.length) h += `<h2>루틴</h2>` + rs.map(r => `<h3>${inl(r.title || '')} <i>${FQ[r.freq] || ''}</i></h3>${(r.changes || []).length ? `<ul>${r.changes.map(c => `<li>❗ ${inl(c.text)} <i>${short(c.date)}</i></li>`).join('')}</ul>` : ''}${(r.log || []).length ? `<p><i>최근 한 날: ${r.log.slice().sort().slice(-5).map(short).join(', ')}</i></p>` : ''}`).join('');
  const nd = items.filter(i => i.kind === 'todo' && !i.date && !i.done); if (nd.length) h += `<h2>날짜 없는 할일</h2><ul>${nd.map(it => `<li>${inl(it.title || '')}${it.area ? ` <i>#${esc(it.area)}</i>` : ''}${(it.checks || []).length ? '<br>❗ ' + it.checks.map(c => inl(c.text)).join(' / ') : ''}</li>`).join('')}</ul>`;
  const mns = (S.rmonths || []).filter(m => /^mn-/.test(m.id) && has(m.blocks)).sort((a, b) => b.id.localeCompare(a.id));
  if (mns.length) h += `<h2>이달 메모 모음</h2>` + mns.map(m => `<h3>${m.id.slice(3, 7)}년 ${+m.id.slice(8, 10)}월</h3>${blocks(m.blocks)}`).join('');
  if (h) out.push({ name: '00 메모 · 루틴 · 날짜 없는 할일', html: page('메모 · 루틴 · 날짜 없는 할일', h) });
  return out;
}
