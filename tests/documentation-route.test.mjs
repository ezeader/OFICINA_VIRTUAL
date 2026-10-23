import test from 'node:test';
import assert from 'node:assert/strict';
import {parseDocumentationRoute,openingsHref} from '../lib/documentation-route.ts';

test('direct opening links retain the project, rubric and pending case on reload',()=>{
 assert.deepEqual(parseDocumentationRoute('#documentacion/angel/aberturas'),{projectId:'angel',rubric:'Aberturas',caseCode:undefined});
 for(const code of ['MC-2275029','MC-2295997','MC-1020586'])assert.equal(parseDocumentationRoute(openingsHref(code)).caseCode,code);
});
test('unrelated or malformed hashes do not navigate to documentation',()=>{
 for(const hash of ['','#marketing','#documentacion/san/aberturas','#documentacion/angel/aberturas/javascript:alert(1)','#documentacion/angel/aberturas/MC-123/more'])assert.equal(parseDocumentationRoute(hash),null);
 assert.equal(openingsHref('anything/else'),'#documentacion/angel/aberturas');
});
test('the structure desk has its own direct link',()=>{
 assert.deepEqual(parseDocumentationRoute('#documentacion/angel/estructura'),{projectId:'angel',rubric:'Estructura'});
 assert.equal(parseDocumentationRoute('#documentacion/angel/estructura/x'),null);
});
