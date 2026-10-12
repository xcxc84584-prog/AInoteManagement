
/* BV-Text v6.2.5 media persistence: per-browser IndexedDB, optional local directory. */
(function(){
'use strict';
const DB='bv-text-media-v625', STORE='media';
let folder=null, busy=new Set();
function db(){return new Promise((ok,fail)=>{const q=indexedDB.open(DB,1);q.onupgradeneeded=()=>q.result.createObjectStore(STORE,{keyPath:'url'});q.onsuccess=()=>ok(q.result);q.onerror=()=>fail(q.error)})}
async function record(url){const d=await db();return new Promise((ok,fail)=>{const t=d.transaction(STORE,'readonly');const q=t.objectStore(STORE).get(url);q.onsuccess=()=>ok(q.result);q.onerror=()=>fail(q.error);t.oncomplete=()=>d.close()})}
async function put(item){const d=await db();return new Promise((ok,fail)=>{const t=d.transaction(STORE,'readwrite');t.objectStore(STORE).put(item);t.oncomplete=()=>{d.close();ok()};t.onerror=()=>fail(t.error)})}
async function digest(url){const bytes=new TextEncoder().encode(url);const hash=await crypto.subtle.digest('SHA-256',bytes);return [...new Uint8Array(hash)].map(x=>x.toString(16).padStart(2,'0')).join('')}
function mimeExt(type){return /svg/i.test(type)?'.svg':/png/i.test(type)?'.png':/webp/i.test(type)?'.webp':/gif/i.test(type)?'.gif':/jpeg|jpg/i.test(type)?'.jpg':'.bin'}
async function writeFolder(item){if(!folder)return;const name=(await digest(item.url))+mimeExt(item.blob.type);const f=await folder.getFileHandle(name,{create:true});const w=await f.createWritable();await w.write(item.blob);await w.close()}
async function load(url){
 if(!url||/^blob:|^asset:|^clipboard-image:/i.test(url))return null;
 const saved=await record(url).catch(()=>null);if(saved?.blob)return saved;
 if(!/^data:image\//i.test(url)&&!/^https?:\/\//i.test(url))return null;
 let blob;
 try{
  if(/^data:/i.test(url)){
   const response=await fetch(url);blob=await response.blob();
  }else{
   // Cross-origin images are cacheable only when the origin permits CORS.
   const response=await fetch(url,{mode:'cors',credentials:'omit',redirect:'follow'});
   if(!response.ok)throw Error('HTTP '+response.status);
   blob=await response.blob();
  }
  if(!blob.type.startsWith('image/')||blob.size>15*1024*1024||!blob.size)throw Error('invalid image or over 15MB');
  if(/svg/i.test(blob.type)){
   const xml=await blob.text();const doc=new DOMParser().parseFromString(xml,'image/svg+xml');
   if(doc.querySelector('parsererror')||doc.documentElement.localName!=='svg')throw Error('invalid SVG');
   doc.querySelectorAll('script,foreignObject,iframe,object,embed,link').forEach(x=>x.remove());
   doc.querySelectorAll('*').forEach(el=>[...el.attributes].forEach(a=>{
    if(/^on/i.test(a.name)||(/^(href|xlink:href)$/i.test(a.name)&&!a.value.startsWith('#'))||(/url\s*\(/i.test(a.value)&&!/url\s*\(\s*#/.test(a.value)))el.removeAttribute(a.name);
   }));
   blob=new Blob([new XMLSerializer().serializeToString(doc.documentElement)],{type:'image/svg+xml'});
  }
  const item={url,blob,time:Date.now()};await put(item);await writeFolder(item).catch(()=>{});
  return item;
 }catch(e){return null}
}
const active=new WeakMap();
async function persistImage(im){
 if(!im.isConnected)return;
 const url=im.dataset.bvOriginalSrc||im.getAttribute('src')||'';
 if(!url||busy.has(url)||/^asset:|^clipboard-image:|^blob:/i.test(url))return;
 busy.add(url);
 try{
  const item=await load(url);
  if(item&&im.isConnected){
   const previous=active.get(im);if(previous)URL.revokeObjectURL(previous);
   const local=URL.createObjectURL(item.blob);active.set(im,local);
   im.dataset.bvOriginalSrc=url;im.src=local;
   im.loading='eager';
  }
 }finally{busy.delete(url)}
}
function scan(root=document){
 root.querySelectorAll('img').forEach(im=>persistImage(im).catch(()=>{}));
}
const observer=new MutationObserver(changes=>{
 for(const change of changes)for(const node of change.addedNodes){
  if(node.nodeType!==1)continue;
  if(node.matches?.('img'))persistImage(node).catch(()=>{});
  else scan(node);
 }
});
function init(){
 scan();observer.observe(document.body,{childList:true,subtree:true});
 const btn=document.createElement('button');
 btn.type='button';btn.id='bv-media-folder-button';btn.textContent='圖片本地資料夾';
 btn.title='授權資料夾後，將已成功擷取的圖片與 SVG 寫入該資料夾；瀏覽器仍保留 IndexedDB 快取';
 btn.style.cssText='position:fixed;bottom:8px;right:8px;z-index:2147483000;background:#25364c;color:#fff;border:1px solid #57718c;border-radius:6px;padding:5px 8px;font-size:12px;opacity:.85;cursor:pointer';
 btn.onclick=async()=>{
  if(!window.showDirectoryPicker){alert('目前瀏覽器或嵌入元件不支援直接選取資料夾。圖片仍會儲存在此瀏覽器的 IndexedDB。');return}
  try{
   folder=await showDirectoryPicker({mode:'readwrite',id:'bv-text-media'});
   const d=await db();const items=await new Promise((ok,fail)=>{const t=d.transaction(STORE,'readonly');const q=t.objectStore(STORE).getAll();q.onsuccess=()=>ok(q.result);q.onerror=()=>fail(q.error);t.oncomplete=()=>d.close()});
   let count=0;for(const item of items){try{await writeFolder(item);count++}catch(e){}}
   btn.textContent='資料夾已授權';alert('已寫入 '+count+' 張已快取圖片。之後載入的圖片將同步存入資料夾。');
  }catch(e){if(e.name!=='AbortError')alert('資料夾授權失敗：'+e.message+'。仍可使用 IndexedDB 快取。')}
 };
 document.body.appendChild(btn);
}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',init);else init();
window.BVMedia625={scan,load};
})();
