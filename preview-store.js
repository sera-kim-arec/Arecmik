// Isolated preview database. Examples exist in memory only and reset on reload.
const clone = value => JSON.parse(JSON.stringify(value));
const today = new Date();
const day = [today.getFullYear(),String(today.getMonth()+1).padStart(2,'0'),String(today.getDate()).padStart(2,'0')].join('-');
const stamp=Date.now();
const dayAt=offset=>{const d=new Date(today);d.setDate(d.getDate()+offset);return [d.getFullYear(),String(d.getMonth()+1).padStart(2,'0'),String(d.getDate()).padStart(2,'0')].join('-');};
const store = {
 projects:[{id:'preview-work',name:'브랜드 리뉴얼',space:'work',status:'active',start:day,memoH:'<div>밝고 편안한 방향으로. 금요일에 시안 확인.</div>',created:stamp,mods:{memo:true}},{id:'preview-life',name:'가을 제주 여행',space:'life',status:'active',start:day,memoH:'<div>동쪽 숙소 · 하루에 한 곳 · 여유롭게</div>',created:stamp,mods:{memo:true}}],
 todos:[{id:'preview-meeting',title:'브랜드 리뉴얼 미팅',kind:'event',date:day,time:'14:00',projectId:'preview-work',space:'work',done:false,created:stamp},{id:'preview-work-task',title:'미팅 전 참고 이미지 모으기',date:day,projectId:'preview-work',space:'work',done:false,created:stamp},{id:'preview-trip',title:'제주 여행 계획 세우기',kind:'event',date:day,time:'',projectId:'preview-life',space:'life',done:false,created:stamp},{id:'preview-life-task',title:'제주 동쪽 숙소 비교하기',projectId:'preview-life',space:'life',done:false,created:stamp}],
 moms:[{id:'preview-work-note',t:'리뉴얼 방향을 정한 날',h:'<div>리뉴얼 방향을 정한 날</div><div>첫 화면에서는 핵심 메시지가 바로 보이도록 다듬기로 했다.</div><div>금요일까지 시안 두 가지 정리하기.</div>',d:day,pid:'preview-work',space:'work',pinned:true,at:stamp},{id:'preview-life-note',t:'이번 여행에서는 천천히',h:'<div>이번 여행에서는 천천히</div><div>하루에 한 곳만 정해서 느긋하게 다녀보기.</div>',d:day,pid:'preview-life',space:'life',pinned:true,at:stamp}],
 notes:[{id:'preview-work-doc',title:'리뉴얼 참고 자료 정리',html:'<div>좋아하는 화면과 참고할 디자인을 모아두는 곳.</div>',space:'work',pid:'preview-work',created:stamp},{id:'preview-life-doc',title:'다시 가고 싶은 제주 장소들',html:'<div>바닷가 카페, 조용한 산책길.</div>',space:'life',pid:'preview-life',created:stamp}],
 logs:[],exps:[],refs:[],ents:[],fbk:[],trash:[],imgs:[]
};
// A few varied examples make density, grouping and collapsed details reviewable.
Object.assign(store.projects[0],{color:'#D1B55D',mods:{memo:true,cost:true,budget:300000},tbl:{on:true,fields:[{k:'stage',n:'단계',t:'sel',o:['준비','검토','완료']},{k:'date',n:'날짜',t:'date'}]}});
store.projects.push({id:'preview-portfolio',name:'나만의 포트폴리오',space:'work',status:'active',start:dayAt(-5),end:dayAt(14),color:'#B9B5A7',memoH:'<div>이번 달에는 가장 좋아하는 작업 세 개부터 정리하기.</div>',created:stamp+1,mods:{memo:true}});
store.todos.push(
 {id:'preview-followup',title:'시안 두 가지 정리해서 공유하기',date:dayAt(2),projectId:'preview-work',space:'work',done:false,created:stamp+1},
 {id:'preview-finished',title:'리뉴얼 방향 정리하기',date:dayAt(-1),doneDate:dayAt(-1),doneAt:stamp-86400000,projectId:'preview-work',space:'work',done:true,created:stamp-86400000},
 {id:'preview-portfolio-task',title:'소개할 작업 세 개 고르기',date:dayAt(1),projectId:'preview-portfolio',space:'work',done:false,created:stamp+2},
 {id:'preview-undated',title:'영감이 된 화면 모아두기',projectId:'preview-work',space:'work',done:false,created:stamp+3}
);
store.moms.push({id:'preview-earlier-note',t:'좋아하는 방향이 조금 더 선명해졌다',h:'<div>좋아하는 방향이 조금 더 선명해졌다</div><div>꾸미기보다 읽기 편한 화면. 작은 선택에도 이유를 남겨두기로 했다.</div>',d:dayAt(-2),pid:'preview-work',space:'work',at:stamp-172800000});
store.notes.push({id:'preview-work-journal',log:true,date:dayAt(-1),space:'work',html:'<div>리뉴얼의 우선순위를 정했다.</div><div>내일 미팅에서는 첫 화면의 메시지부터 이야기하기.</div>',updated:stamp-86400000});
store.ents.push({id:'preview-studio',pid:'preview-work',title:'디자인 스튜디오',v:{stage:'검토',date:day},created:stamp});
store.exps.push({id:'preview-work-expense',t:'참고 도서 구입',a:28000,d:dayAt(-1),pid:'preview-work',sp:'work',c:'자료',created:stamp-86400000});
store.logs.push({id:'memo_work',html:'<div>금요일에는 시안을 확인하고, 결정한 이유도 함께 남기기.</div>'},{id:'memo_life',html:'<div>여행에서는 하루에 한 곳만. 쉬는 시간도 일정에 넣기.</div>'});
store.refs.push(
 {id:'preview-brand-guide',title:'브랜드 컬러·문구',html:'<div>레몬색은 선택한 곳에만. 문구는 짧고 편안하게.</div>',space:'work',fav:true,created:stamp-86400000},
 {id:'preview-review-list',title:'시안 확인 체크리스트',html:'<div>제목이 한눈에 보이는지, 모바일에서 누르기 편한지 확인하기.</div>',space:'work',created:stamp},
 {id:'preview-trip-reference',title:'제주 여행 준비물',html:'<div>신분증, 충전기, 편한 신발.</div>',space:'life',fav:true,created:stamp}
);
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
