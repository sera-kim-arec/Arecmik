// Compare only fields being edited. Firestore transactions do the final check
// against the server; snapshots and local optimistic state are not a lock.
export const copy = value => value === undefined ? null : JSON.parse(JSON.stringify(value));
const ordered = value => Array.isArray(value) ? value.map(ordered) : value && typeof value === 'object'
  ? Object.fromEntries(Object.keys(value).sort().map(key => [key, ordered(value[key])])) : value ?? null;
export const same = (a, b) => JSON.stringify(ordered(a)) === JSON.stringify(ordered(b));
export class EditConflict extends Error {
  constructor(remote, message = '다른 기기에서 내용이 바뀌어 저장을 멈췄어요.') {
    super(message); this.name = 'EditConflict'; this.code = 'edit-conflict'; this.remote = copy(remote);
  }
}
export function checkPatch(base, remote, patch, allowCreate = false) {
  if (!base || (!remote.exists && (!allowCreate || base.exists))) throw new EditConflict(remote);
  const conflicts = [];
  for (const [key, value] of Object.entries(patch)) {
    if (key === 'updated') continue;
    const saved = remote.value?.[key];
    if (!same(saved, base.value?.[key]) && !same(saved, value)) conflicts.push(key);
  }
  if (conflicts.length) throw new EditConflict({...remote, conflicts});
  return patch;
}
export const canRetry = error => /^(unavailable|deadline-exceeded|aborted|cancelled|unknown)$/.test(error?.code || '') || error?.name === 'TypeError';
