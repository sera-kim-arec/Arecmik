// Pure reminder logic shared by the push sender. Mirrors fireTime() in index.html.
export const DEFAULTS = { remindMin: 15, untimed: 'am9' };

function tzOffset(ts, tz) {
  const parts = Object.fromEntries(new Intl.DateTimeFormat('en-US', {
    timeZone: tz, hourCycle: 'h23', year: 'numeric', month: '2-digit', day: '2-digit',
    hour: '2-digit', minute: '2-digit', second: '2-digit'
  }).formatToParts(new Date(ts)).map(p => [p.type, p.value]));
  const asUtc = Date.UTC(+parts.year, +parts.month - 1, +parts.day, +parts.hour, +parts.minute, +parts.second);
  return asUtc - ts;
}
// wall-clock time in `tz` -> epoch ms
export function zoned(y, mo, d, h, mi, tz) {
  const guess = Date.UTC(y, mo - 1, d, h, mi);
  const first = guess - tzOffset(guess, tz);
  return guess - tzOffset(first, tz);
}

export function fireTime(it, settings, tz) {
  if (!it || !it.date || it.done) return null;
  const st = { ...DEFAULTS, ...(settings || {}) };
  const r = it.remind || '';
  if (r === 'off') return null;
  const [y, mo, d] = it.date.split('-').map(Number);
  if (it.start) {
    const mins = r === '' || isNaN(+r) ? +st.remindMin : +r;
    const [h, mi] = it.start.split(':').map(Number);
    return zoned(y, mo, d, h, mi, tz) - mins * 60000;
  }
  const rule = r === '' || !isNaN(+r) ? st.untimed : r;
  if (rule === 'am9') return zoned(y, mo, d, 9, 0, tz);
  if (rule === 'pm6') return zoned(y, mo, d - 1, 18, 0, tz);
  return null;
}

// Reminders that should go out now. Late runs still send up to `lateMs` after the time.
export function dueReminders({ items, settings, tz, now, sent, earlyMs = 3 * 60000, lateMs = 30 * 60000 }) {
  const out = [];
  for (const it of items) {
    const t = fireTime(it, settings, tz);
    if (t == null || t > now + earlyMs || now - t > lateMs) continue;
    const key = `${it.id}|${t}`;
    if (sent[key]) continue;
    out.push({ key, it, t });
  }
  return out;
}

export function message(it, tz) {
  const today = new Intl.DateTimeFormat('en-CA', { timeZone: tz }).format(new Date());
  const [, m, d] = it.date.split('-').map(Number);
  const day = it.date === today ? '오늘' : `${m}월 ${d}일`;
  const kind = it.kind === 'event' ? '일정' : '할일';
  const when = it.start ? `${day} ${it.start}${it.finish ? `–${it.finish}` : ''}` : `${day} · 하루 종일`;
  return { id: it.id, title: it.title || '알림', body: `${kind} · ${when}` };
}
