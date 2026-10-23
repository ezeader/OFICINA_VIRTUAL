export const dynamic='force-dynamic';
// Same-origin delivery avoids client DNS failures. Only the visible viewport
// requests tiles; no prefetch or offline download. OSM attribution stays visible.
export async function GET(req:Request){
 if(!req.headers.get('oai-authenticated-user-id'))return new Response(null,{status:401});
 const q=new URL(req.url).searchParams;
 const values=['z','x','y'].map(k=>q.get(k));
 if(values.some(v=>v===null||!/^\d{1,6}$/.test(v)))return new Response(null,{status:400});
 const [z,x,y]=values.map(Number);
 if(z<4||z>18||x>=2**z||y>=2**z)return new Response(null,{status:400});
 try{
  const upstream=await fetch(`https://tile.openstreetmap.org/${z}/${x}/${y}.png`,{
   headers:{'User-Agent':'AderOffice/1.0 (+https://ader-oficina.ezequielader.chatgpt.site)','Referer':'https://ader-oficina.ezequielader.chatgpt.site/'},
   cf:{cacheEverything:true,cacheTtl:604800},signal:AbortSignal.timeout(15000)
  });
  if(!upstream.ok||!upstream.headers.get('Content-Type')?.startsWith('image/png'))return new Response(null,{status:502});
  const bytes=await upstream.arrayBuffer();if(bytes.byteLength>1024*1024)return new Response(null,{status:502});
  return new Response(bytes,{headers:{'Content-Type':'image/png','Cache-Control':upstream.headers.get('Cache-Control')||'public, max-age=604800','X-Content-Type-Options':'nosniff'}});
 }catch{return new Response(null,{status:503})}
}
