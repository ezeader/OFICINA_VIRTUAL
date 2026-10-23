export const dynamic='force-dynamic';
const shops:Record<string,string>={sanitarias:'bathroom_furnishing|hardware|doityourself|trade',electricas:'electrical|lighting|hardware',albanileria:'building_materials|trade|doityourself|hardware',estructura:'building_materials|trade|hardware',aberturas:'doors|windows|trade',revestimientos:'tiles|flooring|doityourself',pintura:'paint|doityourself',carpinteria:'furniture|kitchen|trade',climatizacion:'heating|trade',gas:'hardware|trade',cubiertas:'building_materials|trade',exteriores:'garden_centre|hardware',todos:'building_materials|bathroom_furnishing|electrical|lighting|hardware|doityourself|trade|tiles|flooring|paint|doors|windows'};
type Feature={geometry:{coordinates:[number,number]};properties:{osm_type:string;osm_id:number;name?:string;street?:string;housenumber?:string;city?:string;state?:string;countrycode?:string;osm_key?:string;osm_value?:string}};
const cache=new Map<string,{at:number;data:unknown}>();const geocache=new Map<string,Feature>();let lastQuery=0;
const reply=(body:unknown,status=200)=>Response.json(body,{status,headers:{'Cache-Control':'private, max-age=60'}});
async function query(url:URL){const r=await fetch(url,{headers:{'User-Agent':'AderOffice/1.0 (+https://ader-oficina.ezequielader.chatgpt.site)'},signal:AbortSignal.timeout(15000)});if(!r.ok)throw Error('El directorio está temporalmente ocupado. Podés continuar en Google Maps.');return await r.json() as {features:Feature[]};}
export async function GET(req:Request){
 if(!req.headers.get('oai-authenticated-user-id'))return reply({error:'Sesión requerida'},401);
 const url=new URL(req.url),zone=(url.searchParams.get('zone')||'').trim(),trade=url.searchParams.get('trade')||'todos',radius=Number(url.searchParams.get('radius')||15);
 if(zone.length<3||zone.length>100||!Object.hasOwn(shops,trade)||![5,15,30].includes(radius))return reply({error:'Indicá una localidad, un rubro y un radio válidos.'},400);
 const key=zone.toLowerCase()+'|'+trade+'|'+radius,cached=cache.get(key);if(cached&&Date.now()-cached.at<3600000)return reply(cached.data);
 if(Date.now()-lastQuery<1500)return reply({error:'Esperá un momento antes de otra búsqueda.'},429);lastQuery=Date.now();
 try{
  let place=geocache.get(zone.toLowerCase());
  if(!place){const geo=new URL('https://photon.komoot.io/api/');geo.searchParams.set('q',zone);geo.searchParams.set('countrycode','AR');geo.searchParams.set('limit','5');const data=await query(geo);place=data.features.find(f=>f.properties.countrycode==='AR');if(!place)return reply({error:'No encontramos esa zona en Argentina. Indicá localidad y provincia.'},404);if(geocache.size>100)geocache.clear();geocache.set(zone.toLowerCase(),place);}
  const [lon,lat]=place.geometry.coordinates;if(!Number.isFinite(lat)||!Number.isFinite(lon))throw Error('Coordenadas no válidas.');
  const nearby=new URL('https://photon.komoot.io/reverse');nearby.searchParams.set('lat',String(lat));nearby.searchParams.set('lon',String(lon));nearby.searchParams.set('radius',String(radius));nearby.searchParams.set('limit','40');for(const tag of shops[trade].split('|'))nearby.searchParams.append('osm_tag','shop:'+tag);
  const raw=await query(nearby);const allowed=new Set(shops[trade].split('|'));
  const results=raw.features.filter(f=>['N','W','R'].includes(f.properties.osm_type)&&Number.isInteger(f.properties.osm_id)&&f.properties.name&&f.properties.countrycode==='AR'&&f.properties.osm_key==='shop'&&allowed.has(f.properties.osm_value||'')).map(f=>{const p=f.properties,[lng,lt]=f.geometry.coordinates;const type=({N:'node',W:'way',R:'relation'} as Record<string,string>)[p.osm_type];return {id:'osm-'+type+'-'+p.osm_id,name:p.name,lat:lt,lon:lng,address:[p.street,p.housenumber,p.city].filter(Boolean).join(' '),contact:'',source:'https://www.openstreetmap.org/'+type+'/'+p.osm_id,kind:p.osm_value};}).filter(p=>Number.isFinite(p.lat)&&Number.isFinite(p.lon));
  const data={center:{lat,lon},zone:[place.properties.name,place.properties.city!==place.properties.name?place.properties.city:'',place.properties.state].filter(Boolean).join(', '),results,readAt:new Date().toISOString(),radiusKm:radius,source:'OpenStreetMap · Photon',exhaustive:false};if(cache.size>100)cache.clear();cache.set(key,{at:Date.now(),data});return reply(data);
 }catch{return reply({error:'El directorio no respondió a tiempo. Las fichas guardadas y Google Maps siguen disponibles.'},503)}
}


