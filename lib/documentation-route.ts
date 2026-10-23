export type DocumentationRoute={projectId:'angel';rubric:'Aberturas';caseCode?:string};

export function parseDocumentationRoute(hash:string):DocumentationRoute|null {
 const match=/^#documentacion\/angel\/aberturas(?:\/(MC-\d+))?\/?$/.exec(hash);
 return match?{projectId:'angel',rubric:'Aberturas',caseCode:match[1]}:null;
}

export function openingsHref(caseCode?:string):string {
 return '#documentacion/angel/aberturas'+(caseCode&&/^MC-\d+$/.test(caseCode)?'/'+caseCode:'');
}
