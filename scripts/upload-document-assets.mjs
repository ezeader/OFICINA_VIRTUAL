import {readFile,writeFile,mkdir} from 'node:fs/promises';
import {resolve,dirname} from 'node:path';
import {createHash} from 'node:crypto';

// Short-lived Sites authorization enters via hidden stdin only. Never log or
// persist it, and never forward it to redirects or another origin.
console.log('Ready for document transfer JSON on stdin (input is hidden).');
if(process.stdin.isTTY)process.stdin.setRawMode(true);
process.stdin.resume();
const input=await new Promise((ok,fail)=>{let raw='';const receive=chunk=>{raw+=chunk.toString();if(raw.includes('\u0003'))process.exit(130);if(/[\r\n]/.test(raw)){process.stdin.off('data',receive);process.stdin.pause();try{ok(JSON.parse(raw.trim()))}catch{fail(Error('Invalid transfer input'))}}};process.stdin.on('data',receive)});
if(process.stdin.isTTY)process.stdin.setRawMode(false);
const {origin,bearer,reportPath}=input;
if(origin!=='https://ader-oficina.ezequielader.chatgpt.site'||!bearer)throw Error('Invalid Site destination');
const manifest=JSON.parse(await readFile('lib/document-assets.json','utf8'));
const auth={'OAI-Sites-Authorization':'Bearer '+bearer,Origin:origin};
const path=resolve(reportPath);await mkdir(dirname(path),{recursive:true});
let previous;try{previous=JSON.parse(await readFile(path,'utf8'))}catch{}
const verified=(previous?.verified??[]).filter(x=>manifest[x.path]?.sha256===x.sha256&&manifest[x.path]?.size===x.size);
const report={startedAt:previous?.startedAt??new Date().toISOString(),verified,failed:[]};
let persistQueue=Promise.resolve();
const persist=()=>{const snapshot=JSON.stringify(report,null,2);persistQueue=persistQueue.then(()=>writeFile(path,snapshot));return persistQueue};
let transferred=verified.reduce((n,x)=>n+x.size,0);
// Upload index data first so the updated interface becomes navigable early.
const entries=Object.entries(manifest).sort(([a,av],[b,bv])=>Number(!/project\.json|native-schedules/.test(a))-Number(!/project\.json|native-schedules/.test(b))||av.size-bv.size);
let stopped=false;
async function transferOne([pathname,entry]){
 let error;
 for(let attempt=1;attempt<=3;attempt++){
  try{
   const bytes=await readFile(resolve('public','.'+pathname));
   if(createHash('sha256').update(bytes).digest('hex')!==entry.sha256)throw Error('Local original changed');
    const uploaded=await fetch(origin+'/api/document-assets?path='+encodeURIComponent(pathname),{method:'PUT',headers:{...auth,'Content-Type':'application/octet-stream'},body:bytes,redirect:'error',signal:AbortSignal.timeout(600000)});
    if(uploaded.status===401||uploaded.status===403)throw Error('Site authorization rejected');
    if(!uploaded.ok)throw Error(`Upload HTTP ${uploaded.status}: ${(await uploaded.text()).slice(0,160)}`);
    const confirmation=await uploaded.json();if(confirmation.sha256!==entry.sha256)throw Error('Upload verification mismatch');
   const downloaded=await fetch(origin+pathname,{headers:auth,redirect:'error',signal:AbortSignal.timeout(180000)});
   if(!downloaded.ok)throw Error(`Readback HTTP ${downloaded.status}`);
   const check=Buffer.from(await downloaded.arrayBuffer());
   if(check.length!==entry.size||createHash('sha256').update(check).digest('hex')!==entry.sha256)throw Error('Remote bytes differ from original');
   report.verified.push({path:pathname,sha256:entry.sha256,size:entry.size});transferred+=entry.size;
   console.log(`${report.verified.length}/${entries.length} verified · ${(transferred/1e6).toFixed(1)} MB · ${pathname}`);
   error=undefined;break;
  }catch(e){error=e;console.log(`Retry ${attempt}/3 · ${pathname} · ${e.message}`);if(/authorization/.test(e.message))break;}
 }
 if(error){report.failed.push({path:pathname,error:error.message});stopped=true;await persist();return}
 await persist();
}
const done=new Set(verified.map(x=>x.path));const pending=entries.filter(([p])=>!done.has(p));let cursor=0;
// Concurrent small files avoid hundreds of serial network round trips. Large
// originals transfer one at a time to bound both Worker and desktop memory.
let largeTail=Promise.resolve();
async function worker(){while(!stopped&&cursor<pending.length){const item=pending[cursor++];if(item[1].size>1024*1024){const before=largeTail;let release;largeTail=new Promise(r=>{release=r});await before;try{if(!stopped)await transferOne(item)}finally{release()}}else await transferOne(item)}}
console.log(`Resuming ${verified.length}/${entries.length}; ${pending.length} pending.`);
await Promise.all(Array.from({length:6},worker));
if(report.failed.length)throw Error(`Transfer paused; ${report.verified.length} documents verified. Resume with the same report.`);
report.completedAt=new Date().toISOString();await persist();
console.log(`Complete: ${report.verified.length} documents read back and SHA-256 verified, ${transferred} original bytes.`);
