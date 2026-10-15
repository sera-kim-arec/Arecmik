// Test adapter: no real Firebase requests. The database survives page reloads.
const clone = value => JSON.parse(JSON.stringify(value));
const store = window.__store;
const listeners = new Map();
const persist = () => sessionStorage.setItem('mock-db', JSON.stringify(store));
// A Firestore document ID and a data field named id are independent.
function documentData(row) {
  const {id, __fieldId, ...data} = row;
  if (Object.hasOwn(row, '__fieldId')) data.id = __fieldId;
  return clone(data);
}
function snapshot(name) {
  return {docs: (store[name] || []).map(row => ({id: row.id, data: () => documentData(row)}))};
}
function emit(name) {
  queueMicrotask(() => (listeners.get(name) || []).forEach(fn => fn(snapshot(name))));
}
function checkWrite(ref, mustExist = false) {
  if (window.__failWrites || window.__failWritesFor === ref.name)
    throw Object.assign(new Error('Simulated write failure'), {code: 'permission-denied'});
  if (mustExist && !(store[ref.name] || []).some(row => row.id === ref.id))
    throw Object.assign(new Error('Missing document'), {code: 'not-found'});
}
async function delayWrite() {
  if (window.__writeDelayMs) await new Promise(resolve => setTimeout(resolve, window.__writeDelayMs));
}
function write(ref, data, merge = false, notify = true) {
  checkWrite(ref);
  const rows = store[ref.name] ||= [];
  const index = rows.findIndex(row => row.id === ref.id);
  const fields = clone(data);
  const row = {...(merge && index >= 0 ? rows[index] : {}), ...fields, id: ref.id};
  if (Object.hasOwn(fields, 'id')) row.__fieldId = fields.id;
  if (index >= 0) rows[index] = row; else rows.push(row);
  (window.__writes ||= []).push({collection: ref.name, id: ref.id, data: clone(data)});
  persist();
  if (notify) emit(ref.name);
}
export const initializeFirestore = () => ({});
export const persistentLocalCache = () => ({});
export const persistentMultipleTabManager = () => ({});
export const collection = (...args) => ({name: args.at(-1)});
export const doc = (...args) => args.length === 1
  ? {...args[0], id: 'test-' + crypto.randomUUID()}
  : args.length === 2 ? {...args[0], id: args[1]}
  : {name: args.at(-2), id: args.at(-1)};
export async function addDoc(ref, data) {
  await delayWrite();
  const result = doc(ref);
  write(result, data);
  return result;
}
export async function setDoc(ref, data, options = {}) {
  await delayWrite(); write(ref, data, !!options.merge);
}
export async function updateDoc(ref, data) {
  await delayWrite(); checkWrite(ref, true); write(ref, data, true);
}
export async function deleteDoc(ref) {
  await delayWrite(); checkWrite(ref);
  store[ref.name] = (store[ref.name] || []).filter(row => row.id !== ref.id);
  persist(); emit(ref.name);
}
export function onSnapshot(ref, callback) {
  const callbacks = listeners.get(ref.name) || [];
  callbacks.push(callback);
  listeners.set(ref.name, callbacks);
  queueMicrotask(() => callback(snapshot(ref.name)));
  return () => listeners.set(ref.name, callbacks.filter(fn => fn !== callback));
}
export async function getDoc(ref) {
  const row = (store[ref.name] || []).find(row => row.id === ref.id);
  return {exists: () => !!row, data: () => row ? documentData(row) : undefined};
}
export async function getDocs(ref) {
  if (window.__failRead === ref.name)
    throw Object.assign(new Error('Read failed'), {code: 'permission-denied'});
  return snapshot(ref.name);
}
export function writeBatch() {
  const actions = [];
  return {
    set: (ref, data) => actions.push({ref, data, merge: false}),
    update: (ref, data) => actions.push({ref, data, merge: true}),
    delete: ref => actions.push({ref, remove: true}),
    commit: async () => {
      await delayWrite();
      actions.forEach(a => checkWrite(a.ref, a.merge));
      actions.forEach(a => {
        if (a.remove) store[a.ref.name] = (store[a.ref.name] || []).filter(row => row.id !== a.ref.id);
        else write(a.ref, a.data, a.merge, false);
      });
      persist();
      new Set(actions.map(a => a.ref.name)).forEach(emit);
    },
  };
}
persist();
