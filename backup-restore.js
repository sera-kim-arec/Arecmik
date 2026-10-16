// Validate the complete format produced by Arecmik; import only missing documents.
export const BACKUP_COLLECTIONS=Object.freeze(['todos','projects','notes','refs','ents','moms','logs','exps','fbk','imgs','trash']);
const reserved=new Set(['__proto__','constructor','prototype']);
function checkValue(value,depth=0){
 if(depth>40)throw new Error('백업 내용이 너무 복잡해요.');
 if(value===null||typeof value==='string'||typeof value==='boolean')return;
 if(typeof value==='number'&&Number.isFinite(value))return;
 if(Array.isArray(value)){for(const v of value)checkValue(v,depth+1);return}
 if(value&&Object.getPrototypeOf(value)===Object.prototype){for(const [key,v] of Object.entries(value)){if(reserved.has(key))throw new Error('지원하지 않는 백업 필드가 있어요.');checkValue(v,depth+1)}return}
 throw new Error('백업 데이터 형식을 확인해 주세요.');
}
export function readBackup(text){
 let data;try{data=JSON.parse(text)}catch(_){throw new Error('JSON 백업 파일을 읽지 못했어요.')}
 if(data?.app!=='Arecmik'||data.version!==1||data.complete!==true||!data.counts)throw new Error('Arecmik의 전체 백업 파일을 선택해 주세요.');
 const encoder=new TextEncoder();
 for(const c of BACKUP_COLLECTIONS){
  if(!Array.isArray(data[c])||data.counts[c]!==data[c].length)throw new Error('백업의 '+c+' 건수가 맞지 않아요. 일부 자료가 빠진 파일은 가져오지 않아요.');
  const ids=new Set();for(const row of data[c]){
   if(!row||typeof row.id!=='string'||!row.id||row.id.includes('/')||/[\u0000-\u001f]/.test(row.id)||['.','..'].includes(row.id)||reserved.has(row.id)||encoder.encode(row.id).length>1500||ids.has(row.id))throw new Error('백업에 잘못되거나 중복된 기록 번호가 있어요.');
   checkValue(row);if(encoder.encode(JSON.stringify(row)).length>1040000)throw new Error('너무 큰 기록이 있어요. 백업 파일을 확인해 주세요.');ids.add(row.id);
  }
 }
 return data;
}
export function backupChunks(rows){
 const chunks=[];let chunk=[],bytes=0;const encoder=new TextEncoder();
 for(const row of rows){const size=encoder.encode(JSON.stringify(row.data)).length+512;if(chunk.length&&(chunk.length>=100||bytes+size>2*1024*1024)){chunks.push(chunk);chunk=[];bytes=0}chunk.push(row);bytes+=size}
 if(chunk.length)chunks.push(chunk);return chunks;
}
