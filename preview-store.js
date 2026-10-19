// Isolated preview database. Examples exist in memory only and reset on reload.
const clone = value => JSON.parse(JSON.stringify(value));
const today = new Date();
const day = [today.getFullYear(),String(today.getMonth()+1).padStart(2,'0'),String(today.getDate()).padStart(2,'0')].join('-');
const stamp=Date.now();
const store = {
 projects:[{id:'preview-work',name:'브랜드 리뉴얼',space:'work',status:'active',start:day,memoH:'<div>밝고 편안한 방향으로. 금요일에 시안 확인.</div>',created:stamp,mods:{memo:true}},{id:'preview-life',name:'가을 제주 여행',space:'life',status:'active',start:day,memoH:'<div>동쪽 숙소 · 하루에 한 곳 · 여유롭게</div>',created:stamp,mods:{memo:true}}],
 todos:[{id:'preview-meeting',title:'브랜드 리뉴얼 미팅',kind:'event',date:day,time:'14:00',projectId:'preview-work',space:'work',done:false,created:stamp},{id:'preview-work-task',title:'미팅 전 참고 이미지 모으기',date:day,projectId:'preview-work',space:'work',done:false,created:stamp},{id:'preview-trip',title:'제주 여행 계획 세우기',kind:'event',date:day,time:'',projectId:'preview-life',space:'life',done:false,created:stamp},{id:'preview-life-task',title:'제주 동쪽 숙소 비교하기',projectId:'preview-life',space:'life',done:false,created:stamp}],
 moms:[{id:'preview-work-note',t:'리뉴얼 방향을 정한 날',h:'<div>리뉴얼 방향을 정한 날</div><div>첫 화면에서는 핵심 메시지가 바로 보이도록 다듬기로 했다.</div><div>금요일까지 시안 두 가지 정리하기.</div>',d:day,pid:'preview-work',space:'work',pinned:true,at:stamp},{id:'preview-life-note',t:'이번 여행에서는 천천히',h:'<div>이번 여행에서는 천천히</div><div>하루에 한 곳만 정해서 느긋하게 다녀보기.</div>',d:day,pid:'preview-life',space:'life',pinned:true,at:stamp}],
 notes:[{id:'preview-work-doc',title:'리뉴얼 참고 자료 정리',html:'<div>좋아하는 화면과 참고할 디자인을 모아두는 곳.</div>',space:'work',pid:'preview-work',created:stamp},{id:'preview-life-doc',title:'다시 가고 싶은 제주 장소들',html:'<div>바닷가 카페, 조용한 산책길.</div>',space:'life',pid:'preview-life',created:stamp}],
 logs:[],exps:[],refs:[],ents:[],fbk:[],trash:[],imgs:[]
};
export const initializeApp=()=>({});
export const getAuth=()=>({});
export const GoogleAuthProvider=class {};
export const onAuthStateChanged=(auth,callback)=>{setTimeout(()=>callback({uid:'arecmik-preview-only'}),0);return ()=>{};};
export const signInWithPopup=async()=>{};
export const signInWithCredential=async()=>{};
export const signOut=async()=>{};
const listeners = new Map();
const persist = () => {};
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
export function onSnapshot(ref, callback, error) {
  if (window.__failSnapshot === ref.name) {
    queueMicrotask(() => error(Object.assign(new Error('Simulated read failure'), {code: 'permission-denied'})));
    return () => {};
  }
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
export async function runTransaction(db, callback) {
  const batch = writeBatch();
  const result = await callback({get: getDoc, set: batch.set, update: batch.update, delete: batch.delete});
  await batch.commit();
  return result;
}
persist();
