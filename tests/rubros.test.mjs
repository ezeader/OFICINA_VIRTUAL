import test from 'node:test';
import assert from 'node:assert/strict';
import {RUBROS,groupRubroSheets} from '../lib/rubros.ts';

test('rubros keep their computability order and unique keys',()=>{
 assert.equal(RUBROS[0].key,'cubierta');
 assert.equal(new Set(RUBROS.map(r=>r.key)).size,RUBROS.length);
});
test('general sheets come first by sector, then element sheets by kind',()=>{
 const g=groupRubroSheets([{number:'CUB-F-CU-01',title:'Ficha',kind:'element',element:'CU-01'},{number:'CUB-01',title:'Planta de techos',sector:'Techos'},{number:'CUB-F-VC-01',title:'Ficha',kind:'element',element:'VC-01'}],{CU:'Faldones',VC:'Vigas'});
 assert.deepEqual(g.map(x=>x.title),['Techos','Fichas · Faldones','Fichas · Vigas']);
});
