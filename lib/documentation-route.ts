// Links directos a cada rubro de Documentación de Casa Ángel: #documentacion/angel/<rubro>.
// Oficinas Urbetrack: #documentacion/urbe/<clave> con las claves de URBE_RUBROS.
import {URBE_RUBROS} from './rubros';
export type DocumentationRoute={projectId:'angel'|'urbe';rubric:string;caseCode?:string};

const SLUGS:Record<string,string>={aberturas:'Aberturas',estructura:'Estructura',cubierta:'Cubierta',albanileria:'Albañilería',pisos:'Pisos',revestimientos:'Revestimientos',climatizacion:'Climatización',pileta:'Pileta',parrilla:'Parrilla',solar:'Paneles solares',gas:'Gas',domotica:'Domótica',sanitaria:'Sanitaria',electrica:'Eléctrica',cielorrasos:'Cielorrasos',exteriores:'Exteriores',equipamiento:'Equipamiento',mesadas:'Mesadas'};

export function parseDocumentationRoute(hash:string):DocumentationRoute|null {
 const opening=/^#documentacion\/angel\/aberturas(?:\/(MC-\d+))?\/?$/.exec(hash);
 if(opening)return {projectId:'angel',rubric:'Aberturas',caseCode:opening[1]};
 const urbe=/^#documentacion\/urbe(?:\/([a-z]+))?\/?$/.exec(hash),urbeRubro=urbe&&(URBE_RUBROS.find(r=>r.key===urbe[1])||URBE_RUBROS[0]);
 if(urbeRubro)return {projectId:'urbe',rubric:urbeRubro.name};
 const match=/^#documentacion\/angel\/([a-z]+)\/?$/.exec(hash);
 return match&&SLUGS[match[1]]?{projectId:'angel',rubric:SLUGS[match[1]]}:null;
}

export function openingsHref(caseCode?:string):string {
 return '#documentacion/angel/aberturas'+(caseCode&&/^MC-\d+$/.test(caseCode)?'/'+caseCode:'');
}
export const structureHref=()=>'#documentacion/angel/estructura';
export function urbeRubricHref(name:string){const r=URBE_RUBROS.find(x=>x.name===name);return r?'#documentacion/urbe/'+r.key:''}
export function rubricHref(name:string){const slug=Object.entries(SLUGS).find(([,n])=>n===name)?.[0];return slug?'#documentacion/angel/'+slug:''}
