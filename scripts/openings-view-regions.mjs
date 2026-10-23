// Ubica cada dibujo de Aberturas dentro de su lámina para los botones "ampliar" (como en Sanitarias).
// Lee el SVG exportado de cada vista: su transform indica dónde estaba recortada en la hoja.
// Uso: node scripts/openings-view-regions.mjs  → public/casa-angel/openings/view-regions.json
import fs from 'node:fs';
import path from 'node:path';
import zlib from 'node:zlib';

const dir=path.resolve('public/casa-angel/openings');

// Región [x0,y0,x1,y1] en fracción de la hoja (origen arriba a la izquierda), o null si no se puede leer.
export function regionFromSvg(svg){
 const size=/<svg[^>]*\bwidth="([\d.]+)"[^>]*\bheight="([\d.]+)"/.exec(svg);
 const move=/matrix\(1,0,0,-1,(-?[\d.]+),(-?[\d.]+)\)/.exec(svg);
 const sheet=/d="M-([\d.]+)-([\d.]+)H\1V\2H-\1Z"/.exec(svg); // contorno completo de la hoja, centrado en el origen
 if(!size||!move||!sheet)return null;
 const w=+size[1],h=+size[2],tx=+move[1],ty=+move[2],halfW=+sheet[1],halfH=+sheet[2];
 const x0=halfW-tx,y0=halfH-ty,W=halfW*2,H=halfH*2;
 const r=[x0/W,y0/H,(x0+w)/W,(y0+h)/H].map(n=>Math.round(n*10000)/10000);
 return r.every(n=>n>=-0.01&&n<=1.01)?r:null;
}

export function viewsOf(manifest){
 const docs=[...manifest.rooms,...manifest.items.map(i=>i.documentation),...(manifest.reviewCases||[]).map(c=>c.context)].filter(Boolean);
 const r4=(manifest.documentationR4?.sheets||[]).flatMap(g=>g.sheets.flatMap(s=>s.views));
 return [...docs.flatMap(d=>d.views||[]),...r4];
}

if(process.argv[1]&&path.resolve(process.argv[1])===path.resolve(new URL(import.meta.url).pathname.replace(/^\/(\w:)/,'$1'))){
 const manifest=JSON.parse(fs.readFileSync(path.join(dir,'manifest.json'),'utf8'));
 const out={};let missing=0;
 for(const v of viewsOf(manifest)){
  const file=path.join(dir,path.basename(v.image||''));
  if(!v.image||!fs.existsSync(file)){missing++;continue}
  const raw=fs.readFileSync(file),svg=(raw[0]===31?zlib.gunzipSync(raw):raw).toString('utf8',0,20000);
  const region=regionFromSvg(svg);if(region)out[v.id]=region;else missing++;
 }
 fs.writeFileSync(path.join(dir,'view-regions.json'),JSON.stringify(out));
 console.log(`${Object.keys(out).length} vistas ubicadas, ${missing} sin ubicar`);
}
