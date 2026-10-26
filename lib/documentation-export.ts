import {mergePdfSources,uniquePdfSources} from './pdf-export.mjs';
import {RUBROS,URBE_RUBROS,type RubroManifest} from './rubros';
import {buildSheets,sheetIndex} from './openings-sheets';

import {saveFile,exportName,type ExportProject,type ExportedFile} from './export-files';
import {loadCompressedJson} from '../components/compressed-drawing';
const urbeBase='/urbetrack/rubros',angelBase='/casa-angel/rubros';
const byNumber=(a:{number:string},b:{number:string})=>a.number.localeCompare(b.number,'es',{numeric:true});
async function manifest<T>(url:string):Promise<T|null>{const r=await fetch(url);if(!r.ok)throw Error('No se pudo leer el manifiesto: '+url);return r.json() as Promise<T>}
const sheetPdfs=(sheets?:{number:string;pdf?:string}[])=>{const missing=(sheets||[]).filter(s=>!s.pdf);if(missing.length)throw Error('Hay láminas sin PDF publicado: '+missing.map(s=>s.number).join(', '));return [...(sheets||[])].sort(byNumber).map(s=>s.pdf!)};

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
  if(rubro==='Sanitaria'){const m=await loadCompressedJson('/casa-angel/r13/project.json.gz') as {sheets:{number:string;pdf:string}[]};list=sheetPdfs(m.sheets)}
  else if(rubro==='Estructura')list=sheetPdfs((await manifest<{sheets?:{number:string;pdf?:string}[]}>('/casa-angel/structure/manifest.json'))?.sheets);
  else if(rubro==='Aberturas'){const m=await manifest<Parameters<typeof buildSheets>[0]>('/casa-angel/openings/manifest.json');if(m)list=sheetPdfs(sheetIndex(buildSheets(m)))}
  else{const r=RUBROS.find(x=>x.name===rubro);if(r)list=sheetPdfs((await manifest<RubroManifest>(`${angelBase}/${r.key}/manifest.json`))?.sheets)}
 }
 return uniquePdfSources(list);
}

// Merge source PDF pages without rasterizing or changing their dimensions.
export async function exportRubros(project:ExportProject,rubros:string[],mode:'juntos'|'separados',onProgress?:(text:string)=>void):Promise<ExportedFile[]>{
 if(!rubros.length)throw Error('Elegí al menos un rubro.');
 const sources=new Map<string,string[]>();
 for(const r of rubros){onProgress?.('Revisando '+r);const urls=await rubroPdfs(project.id,r);if(!urls.length)throw Error(r+': todavía no tiene láminas PDF publicadas. Quitá este rubro de la selección.');sources.set(r,urls)}
 const files:ExportedFile[]=[];
 for(const names of mode==='juntos'?[rubros]:rubros.map(r=>[r])){
  try{
   const label=names.join(', ');
   const merged=await mergePdfSources(names.flatMap(r=>sources.get(r)!),{title:project.name+' · '+label,onProgress:(i=0,total=0)=>onProgress?.(`${label} · PDF ${i} de ${total}`),read:async(url:string)=>{const response=await fetch(url);if(!response.ok)throw Error('Falta el PDF '+url);return response.arrayBuffer()}});
   onProgress?.('Guardando en Archivos…');
   const blob=new Blob([merged.bytes as BlobPart],{type:'application/pdf'});
   files.push(await saveFile(project.id,{name:exportName(project.name,label,'pdf'),format:'pdf',rubros:names,sheets:merged.pages},blob));
  }catch(e){throw Error((files.length?`${files.length} PDF ya guardado(s) en Archivos. `:'')+(e instanceof Error?e.message:'No se pudo exportar.'))}
 }
 return files;
}
