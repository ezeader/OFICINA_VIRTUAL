// A link fragment identifies a landing page, not a separate PDF document.
export const uniquePdfSources=urls=>[...new Set(urls.map(url=>url.split('#')[0]))];
export async function mergePdfSources(urls,{read,title,onProgress=(_index=0,_total=0)=>{}}){
 const {PDFDocument}=await import('pdf-lib');
 const doc=await PDFDocument.create();doc.setTitle(title);doc.setAuthor('Studio Ader');
 const sources=uniquePdfSources(urls);
 if(!sources.length)throw Error('No hay PDF publicados para exportar.');
 for(const [i,url] of sources.entries()){
  if(!url.startsWith('/')||url.startsWith('//'))throw Error('Ruta de lámina inválida.');
  onProgress(i+1,sources.length);
  const src=await PDFDocument.load(await read(url));
  for(const page of await doc.copyPages(src,src.getPageIndices()))doc.addPage(page);
 }
 return {bytes:await doc.save(),pages:doc.getPageCount()};
}
