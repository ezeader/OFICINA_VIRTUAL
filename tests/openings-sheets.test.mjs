import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {buildSheets,groupSheets} from '../lib/openings-sheets.ts';
import {regionFromSvg} from '../scripts/openings-view-regions.mjs';

const manifest=JSON.parse(fs.readFileSync(new URL('../public/casa-angel/openings/manifest.json',import.meta.url),'utf8'));
const r2=structuredClone(manifest);delete r2.documentationR4;for(const r of r2.rooms)delete r.r4;

test('sheets are organised like Sanitarias: by level, by opening type and review cases',()=>{
 const cards=buildSheets(r2);
 assert.equal(cards.filter(c=>c.tab==='locales').length,r2.rooms.filter(r=>r.image&&r.items.length).length);
 assert.equal(cards.filter(c=>c.tab==='aberturas').length,r2.items.filter(i=>i.documentation?.image).length);
 assert.equal(cards.filter(c=>c.tab==='revision').length,(r2.reviewCases||[]).length);
 const levels=groupSheets(cards,'locales').map(g=>g.title);
 assert.deepEqual(levels,[...levels].sort((a,b)=>a.localeCompare(b,'es',{numeric:true})));
 assert.deepEqual(groupSheets(cards,'aberturas').map(g=>g.title),['Ventanas','Puertas','Muros cortina']);
 const windows=groupSheets(cards,'aberturas')[0].sheets.map(s=>s.name.split(' · ')[0]);
 assert.deepEqual(windows,[...windows].sort((a,b)=>a.localeCompare(b,'es',{numeric:true})));
});
test('every drawing keeps its element code and a readable name',()=>{
 const el=buildSheets(r2).find(c=>c.name.startsWith('V-155'));
 assert.deepEqual(el.views.map(v=>v.name),['Planta','Axonométrica','Vista frontal','Corte']);
 assert.ok(el.views.every(v=>v.code==='V-155'));
});
test('R4 room sheets replace the R2 room sheet when present, one card per page',()=>{
 const m=structuredClone(r2),room=m.rooms[0];
 room.r4={sheets:[1,2].map(n=>({sheetId:'9'+n,sheetNumber:'ABR-R4-PB-0'+n,image:`/p${n}.svg.gz`,views:[{id:n,name:'Planta del local',scale:20,kind:'plan',image:'/v'}]}))};
 const cards=buildSheets(m).filter(c=>c.roomId===room.id);
 assert.deepEqual(cards.map(c=>[c.number,c.name.endsWith('hoja '+c.number.slice(-1))]),[['ABR-R4-PB-01',true],['ABR-R4-PB-02',true]]);
});
test('a drawing is located on its sheet from the exported SVG transform',()=>{
 const svg='<svg width="241.5" height="242.5"><path transform="matrix(1,0,0,-1,698.96,544.97)" d="M-698.9 302.4H-457.4V544.9Z"/><path d="M-1191.97-841.89H1191.97V841.89H-1191.97Z"/></svg>';
 assert.deepEqual(regionFromSvg(svg),[0.2068,0.1763,0.3081,0.3204]);
 assert.equal(regionFromSvg('<svg></svg>'),null);
});
