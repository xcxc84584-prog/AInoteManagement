/* v6.1: browser-local TOC. IndexedDB is scoped to the browser origin. */
const BV61TOC=(()=>{
 const dbName='bvtext-v61-toc',store='entries';let dbPromise;
 function db(){return dbPromise||(dbPromise=new Promise((resolve,reject)=>{const r=indexedDB.open(dbName,1);r.onupgradeneeded=()=>{const d=r.result;if(!d.objectStoreNames.contains(store)){const s=d.createObjectStore(store,{keyPath:'id'});s.createIndex('document_id','document_id',{unique:false})}};r.onsuccess=()=>resolve(r.result);r.onerror=()=>reject(r.error)}))}
 async function transaction(mode,work){const d=await db();return new Promise((resolve,reject)=>{const t=d.transaction(store,mode),s=t.objectStore(store);let result;const r=work(s);r.onsuccess=()=>result=r.result;r.onerror=()=>reject(r.error);t.oncomplete=()=>resolve(result);t.onerror=()=>reject(t.error)})}
 const list=async id=>(await transaction('readonly',s=>s.index('document_id').getAll(id))).sort((a,b)=>a.lineStart-b.lineStart||a.columnStart-b.columnStart);
 const put=e=>transaction('readwrite',s=>s.put(e));const remove=id=>transaction('readwrite',s=>s.delete(id));
 function lineColumn(text,offset){const before=text.slice(0,offset),last=before.lastIndexOf('\n');return {line:before.split('\n').length,column:offset-last-1}}
 function create(doc,text,start,end,selected){const a=lineColumn(text,start),b=lineColumn(text,end);return {id:crypto.randomUUID(),document_id:doc,title:selected.trim().slice(0,300),selectedText:selected,lineStart:a.line,lineEnd:b.line,columnStart:a.column,columnEnd:b.column,context:text.slice(Math.max(0,start-40),Math.min(text.length,end+40)),createdAt:new Date().toISOString()}}
 function locate(text,e){const lines=text.split('\n'),line=lines[e.lineStart-1]||'';if(line.slice(e.columnStart).startsWith(e.selectedText.split('\n')[0]))return {line:e.lineStart,column:e.columnStart};let at=text.indexOf(e.selectedText);if(at<0||text.indexOf(e.selectedText,at+1)>=0)return null;return lineColumn(text,at)}
 return {list,put,remove,create,locate};
})();
