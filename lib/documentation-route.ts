// Links directos a cada rubro de Documentación de Casa Ángel: #documentacion/angel/<rubro>.
export type DocumentationRoute={projectId:'angel';rubric:string;caseCode?:string};

const SLUGS:Record<string,string>={aberturas:'Aberturas',estructura:'Estructura',cubierta:'Cubierta',albanileria:'Albañilería',pisos:'Pisos',revestimientos:'Revestimientos',climatizacion:'Climatización',pileta:'Pileta',parrilla:'Parrilla',solar:'Paneles solares',gas:'Gas',domotica:'Domótica',sanitaria:'Sanitaria',electrica:'Eléctrica'};

export function parseDocumentationRoute(hash:string):DocumentationRoute|null {
 const opening=/^#documentacion\/angel\/aberturas(?:\/(MC-\d+))?\/?$/.exec(hash);
 if(opening)return {projectId:'angel',rubric:'Aberturas',caseCode:opening[1]};
 const match=/^#documentacion\/angel\/([a-z]+)\/?$/.exec(hash);
 return match&&SLUGS[match[1]]?{projectId:'angel',rubric:SLUGS[match[1]]}:null;
}

export function openingsHref(caseCode?:string):string {
 return '#documentacion/angel/aberturas'+(caseCode&&/^MC-\d+$/.test(caseCode)?'/'+caseCode:'');
}
export const structureHref=()=>'#documentacion/angel/estructura';
export function rubricHref(name:string){const slug=Object.entries(SLUGS).find(([,n])=>n===name)?.[0];return slug?'#documentacion/angel/'+slug:''}
