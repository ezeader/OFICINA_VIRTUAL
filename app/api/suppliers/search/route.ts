export const dynamic='force-dynamic';
const shops:Record<string,string>={sanitarias:'bathroom_furnishing|hardware|doityourself|trade',electricas:'electrical|lighting|hardware',albanileria:'building_materials|trade|doityourself|hardware',estructura:'building_materials|trade|hardware',aberturas:'doors|windows|trade',revestimientos:'tiles|flooring|doityourself',pintura:'paint|doityourself',carpinteria:'furniture|kitchen|trade',climatizacion:'heating|trade',gas:'hardware|trade',cubiertas:'building_materials|trade',exteriores:'garden_centre|hardware',todos:'building_materials|bathroom_furnishing|electrical|lighting|hardware|doityourself|trade|tiles|flooring|paint|doors|windows'};
const cache=new Map<string,{at:number;data:unknown}>();let lastGeo=0;
const reply=(body:unknown,status=200)=>Response.json(body,{status,headers:{'Cache-Control':'private, max-age=60'}});
export async function GET(req:Request){
 if(!req.headers.get('oai-authenticated-user-id'))return reply({error:'Sesión requerida'},401);
 const url=new URL(req.url),zone=(url.searchParams.get('zone')||'').trim(),trade=url.searchParams.get('trade')||'todos';
 if(zone.length<3||zone.length>100||!shops[trade])return reply({error:'Indicá una localidad y un rubro válidos.'},400);
 const key=zone.toLowerCase()+'|'+trade,cached=cache.get(key);if(cached&&Date.now()-cached.at<3600000)return reply(cached.data);
 if(Date.now()-lastGeo<1500)return reply({error:'Esperá un momento antes de otra búsqueda.'},429);lastGeo=Date.now();
 try{
  const geo=await fetch('https://nominatim.openstreetmap.org/search?format=jsonv2&limit=1&countrycodes=ar&q='+encodeURIComponent(zone),{headers:{'User-Agent':'AderOffice/1.0 (+https://ader-oficina.ezequielader.chatgpt.site)'},signal:AbortSignal.timeout(12000)});
  if(!geo.ok)throw Error('El servicio de ubicación no está disponible.');const locations=await geo.json() as {lat:string;lon:string;display_name:string}[];
  if(!locations.length)return reply({error:'No encontramos esa localidad en Argentina. Probá con ciudad y provincia.'},404);
  const lat=Number(locations[0].lat),lon=Number(locations[0].lon);if(!Number.isFinite(lat)||!Number.isFinite(lon))throw Error('Ubicación no válida.');
  const query=`[out:json][timeout:20];nwr(around:15000,${lat},${lon})[shop~"^(${shops[trade]})$"][name];out center tags 60;`;
  const response=await fetch('https://overpass-api.de/api/interpreter?data='+encodeURIComponent(query),{headers:{'User-Agent':'AderOffice/1.0 (+https://ader-oficina.ezequielader.chatgpt.site)'},signal:AbortSignal.timeout(25000)});
  if(!response.ok)throw Error('La búsqueda de comercios está temporalmente ocupada. Volvé a intentar.');
  const raw=await response.json() as {elements:{type:string;id:number;lat?:number;lon?:number;center?:{lat:number;lon:number};tags:Record<string,string>}[];remark?:string};
  if(raw.remark)throw Error('La búsqueda quedó incompleta. Volvé a intentar.');
  const results=(raw.elements||[]).map(e=>({id:'osm-'+e.type+'-'+e.id,name:e.tags.name,lat:e.lat??e.center?.lat,lon:e.lon??e.center?.lon,address:[e.tags['addr:street'],e.tags['addr:housenumber'],e.tags['addr:city']].filter(Boolean).join(' '),contact:e.tags['contact:phone']||e.tags.phone||'',website:/^https?:\/\//i.test(e.tags.website||e.tags['contact:website']||'')?(e.tags.website||e.tags['contact:website']):'',source:`https://www.openstreetmap.org/${e.type}/${e.id}`,kind:e.tags.shop})).filter(e=>Number.isFinite(e.lat)&&Number.isFinite(e.lon));
  const data={center:{lat,lon},zone:locations[0].display_name,results,readAt:new Date().toISOString(),radiusKm:15};
  if(cache.size>100)cache.clear();cache.set(key,{at:Date.now(),data});return reply(data);
 }catch(e){return reply({error:(e as Error).name==='TimeoutError'?'El directorio demoró demasiado. Volvé a intentar; las fichas verificadas siguen disponibles.':(e as Error).message||'No se pudo completar la búsqueda.'},503)}
}
