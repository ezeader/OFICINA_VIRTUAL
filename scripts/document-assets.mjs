import {readdir,readFile,writeFile,rm} from 'node:fs/promises';
import {resolve,relative,sep} from 'node:path';
import {createHash} from 'node:crypto';

const root=resolve('public/casa-angel');
const manifest={};
const types={'.pdf':'application/pdf','.svg':'image/svg+xml','.png':'image/png','.json':'application/json','.gz':'application/gzip','.jpg':'image/jpeg','.jpeg':'image/jpeg','.webp':'image/webp'};
for(const entry of await readdir(root,{recursive:true,withFileTypes:true})){
 if(!entry.isFile())continue;
 const full=resolve(entry.parentPath??entry.path,entry.name);
 const bytes=await readFile(full);
 const pathname='/casa-angel/'+relative(root,full).split(sep).join('/');
 const suffix=entry.name.slice(entry.name.lastIndexOf('.'));
 manifest[pathname]={size:bytes.length,sha256:createHash('sha256').update(bytes).digest('hex'),type:types[suffix]??'application/octet-stream'};
}
const sorted=Object.fromEntries(Object.entries(manifest).sort(([a],[b])=>a.localeCompare(b)));
const body=JSON.stringify(sorted,null,2)+'\n';
const target=resolve('lib/document-assets.json');
if(process.argv.includes('--check')){
 if(await readFile(target,'utf8')!==body)throw Error('El inventario de documentos cambió. Ejecutá node scripts/document-assets.mjs antes de publicar.');
}else await writeFile(target,body);
if(process.argv.includes('--exclude-built-copies')){
 // Only the generated copy is excluded. Original documents remain tracked and
 // every byte is uploaded to private R2 before publication is declared complete.
 const builtRoot=resolve('dist/client');
 const copies=resolve(builtRoot,'casa-angel');
 if(!copies.startsWith(builtRoot+sep)||copies===root)throw Error('Invalid build directory');
 await rm(copies,{recursive:true,force:true});
}
console.log(`${Object.keys(sorted).length} documentos; ${Object.values(sorted).reduce((n,x)=>n+x.size,0)} bytes originales conservados.`);
