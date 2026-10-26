export type ExportProject={id:string;name:string};
export type ExportedFile={id:string;projectId:string;name:string;format:'pdf'|'xlsx';rubros:string[];sheets:number;size:number;date:string};
export const FILES_CHANGED='ader-archivos-cambio';
export const fileUrl=(f:ExportedFile,download=false)=>`/api/exports?project=${encodeURIComponent(f.projectId)}&id=${f.id}${download?'&download=1':''}`;
async function read<T>(r:Response):Promise<T>{if(!r.ok){let message='No se pudo acceder a Archivos.';try{message=((await r.json()) as {error?:string}).error||message}catch{}throw Error(message)}return r.json()}
export async function saveFile(projectId:string,meta:Omit<ExportedFile,'id'|'projectId'|'size'|'date'>,blob:Blob){
 const f=await read<ExportedFile>(await fetch(`/api/exports?project=${encodeURIComponent(projectId)}`,{method:'PUT',headers:{'Content-Type':blob.type,'X-Export-Metadata':encodeURIComponent(JSON.stringify(meta))},body:blob}));
 window.dispatchEvent(new Event(FILES_CHANGED));return f;
}
export async function listFiles(projectId:string){return read<ExportedFile[]>(await fetch(`/api/exports?project=${encodeURIComponent(projectId)}`,{cache:'no-store'}))}
export function exportName(project:string,label:string,extension:string){return `${project} - ${label}`.replace(/[\r\n\/\\]/g,' ').slice(0,150)+` - ${new Date().toISOString().slice(0,10)}.${extension}`}
