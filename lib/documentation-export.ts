// Exportación de láminas por rubro a PDF y archivo local de exportaciones (pestaña Archivos).
// Las láminas salen de los mismos manifiestos que muestra Documentación; los PDF generados se guardan
// en este navegador (IndexedDB) para descargarlos después desde Archivos.
import {RUBROS,URBE_RUBROS,type RubroManifest} from './rubros';
import {buildSheets,sheetIndex} from './openings-sheets';

export type ExportProject={id:string;name:string};
export type ExportedFile={id:string;projectId:string;name:string;rubros:string[];sheets:number;size:number;date:string;blob:Blob};

const urbeBase='/urbetrack/rubros',angelBase='/casa-angel/rubros';
const byNumber=(a:{number:string},b:{number:string})=>a.number.localeCompare(b.number,'es',{numeric:true});
async function manifest<T>(url:string):Promise<T|null>{const r=await fetch(url);return r.ok?r.json() as Promise<T>:null}
const sheetPdfs=(sheets?:{number:string;pdf?:string}[])=>[...(sheets||[])].sort(byNumber).map(s=>s.pdf).filter((p):p is string=>!!p);

// Rubros exportables de cada proyecto, en el orden de Documentación.
export function exportableRubros(projectId:string):string[]{
 if(projectId==='urbe')return URBE_RUBROS.map(r=>r.name);
 if(projectId==='angel')return ['Sanitaria','Aberturas','Estructura',...RUBROS.map(r=>r.name)];
 return [];
}

// PDF de cada lámina del rubro, sin repetir archivos (una lámina puede compartir PDF con otras).
export async function rubroPdfs(projectId:string,rubro:string):Promise<string[]>{
 let list:string[]=[];
 if(projectId==='urbe'){const r=URBE_RUBROS.find(x=>x.name===rubro);if(r)list=sheetPdfs((await manifest<RubroManifest>(`${urbeBase}/${r.key}/manifest.json`))?.sheets)}
 else if(projectId==='angel'){
  if(rubro==='Sanitaria')list=['/casa-angel/Documentacion-Sanitarias-original.pdf'];
  else if(rubro==='Estructura')list=sheetPdfs((await manifest<{sheets?:{number:string;pdf?:string}[]}>('/casa-angel/structure/manifest.json'))?.sheets);
  else if(rubro==='Aberturas'){const m=await manifest<Parameters<typeof buildSheets>[0]>('/casa-angel/openings/manifest.json');if(m)list=sheetIndex(buildSheets(m)).map(s=>s.pdf).filter((p):p is string=>!!p)}
  else{const r=RUBROS.find(x=>x.name===rubro);if(r)list=sheetPdfs((await manifest<RubroManifest>(`${angelBase}/${r.key}/manifest.json`))?.sheets)}
 }
 return [...new Set(list)];
}

const stamp=()=>new Date().toISOString().slice(0,10);
const fileName=(project:ExportProject,label:string)=>`${project.name} · ${label} · ${stamp()}.pdf`;

// mode 'juntos': un solo PDF con todos los rubros elegidos; 'separados': un PDF por rubro.
export async function exportRubros(project:ExportProject,rubros:string[],mode:'juntos'|'separados',onProgress?:(text:string)=>void):Promise<ExportedFile[]>{
 const {PDFDocument}=await import('pdf-lib');
 const cache=new Map<string,ArrayBuffer>();
 const append=async(target:Awaited<ReturnType<typeof PDFDocument.create>>,url:string)=>{
  if(!cache.has(url)){const r=await fetch(url);if(!r.ok)throw Error('No se pudo leer '+url);cache.set(url,await r.arrayBuffer())}
  const src=await PDFDocument.load(cache.get(url)!,{ignoreEncryption:true});
  for(const page of await target.copyPages(src,src.getPageIndices()))target.addPage(page);
 };
 const build=async(names:string[],label:string)=>{
  const doc=await PDFDocument.create();doc.setTitle(`${project.name} · ${label}`);doc.setAuthor('Ader Studio');
  for(const rubro of names){
   const pdfs=await rubroPdfs(project.id,rubro);
   for(const [i,url] of pdfs.entries()){onProgress?.(`${rubro} · lámina ${i+1} de ${pdfs.length}`);await append(doc,url)}
  }
  if(!doc.getPageCount())return null;
  const bytes=await doc.save(),blob=new Blob([bytes as BlobPart],{type:'application/pdf'});
  return {id:crypto.randomUUID(),projectId:project.id,name:fileName(project,label),rubros:names,sheets:doc.getPageCount(),size:blob.size,date:new Date().toISOString(),blob} satisfies ExportedFile;
 };
 const all=exportableRubros(project.id);
 const jobs=mode==='juntos'?[[rubros,rubros.length===all.length?'Documentación completa':rubros.join(', ')] as const]:rubros.map(r=>[[r],r] as const);
 const files:ExportedFile[]=[];
 for(const [names,label] of jobs){const f=await build([...names],label);if(f){await saveFile(f);files.push(f)}}
 return files;
}

// Archivo local de exportaciones.
const DB='ader-archivos',STORE='exportaciones';
function open():Promise<IDBDatabase>{return new Promise((ok,fail)=>{const r=indexedDB.open(DB,1);r.onupgradeneeded=()=>r.result.createObjectStore(STORE,{keyPath:'id'});r.onsuccess=()=>ok(r.result);r.onerror=()=>fail(r.error)})}
async function run<T>(mode:IDBTransactionMode,fn:(s:IDBObjectStore)=>IDBRequest<T>):Promise<T>{const db=await open();return new Promise((ok,fail)=>{const r=fn(db.transaction(STORE,mode).objectStore(STORE));r.onsuccess=()=>ok(r.result);r.onerror=()=>fail(r.error)})}
export const saveFile=(f:ExportedFile)=>run('readwrite',s=>s.put(f));
export const deleteFile=(id:string)=>run('readwrite',s=>s.delete(id));
export async function listFiles(projectId:string):Promise<ExportedFile[]>{return (await run<ExportedFile[]>('readonly',s=>s.getAll())).filter(f=>f.projectId===projectId).sort((a,b)=>b.date.localeCompare(a.date))}
export const FILES_CHANGED='ader-archivos-cambio';
export function downloadFile(f:ExportedFile){const url=URL.createObjectURL(f.blob),a=document.createElement('a');a.href=url;a.download=f.name;a.click();setTimeout(()=>URL.revokeObjectURL(url),10000)}
