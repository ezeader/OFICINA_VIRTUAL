import test from 'node:test';
import assert from 'node:assert/strict';
import {groupRubroLevels} from '../lib/rubros.ts';

const sheets=[
 {number:'CLI-00',title:'Índice',level:'General',sector:'General',kind:'general'},
 {number:'CLI-PA-01',title:'Piso radiante · 01. Planta Alta',level:'01. Planta Alta',sector:'R19 previo · 01. Planta Alta',kind:'general'},
 {number:'CLI-P-PA',title:'Trazado de serpentines · 01. Planta Alta',level:'01. Planta Alta',sector:'1 · Plantas con serpentina',kind:'general'},
 {number:'CLI-CO-S',title:'Colector CO-S · detalle',level:'01. Planta Alta',sector:'2 · Colectores',kind:'general'},
 {number:'CLI-P-PB',title:'Trazado de serpentines · 00. Planta Baja',level:'00. Planta Baja',sector:'1 · Plantas con serpentina',kind:'general'},
 {number:'CLI-F-01',title:'Ficha',level:'00. Planta Baja',sector:'00. Planta Baja',kind:'element',element:'SE-01'},
 {number:'CLI-D-01',title:'Detalle',level:'Detalles',sector:'Detalles',kind:'general'},
];
test('each level opens with its full plan, levels in order, previous versions last and the index at the end',()=>{
 const {levels,others}=groupRubroLevels(sheets,{SE:'Serpentina'});
 assert.deepEqual(levels.map(l=>l.level),['00. Planta Baja','01. Planta Alta']);
 assert.equal(levels[0].plan.number,'CLI-P-PB');
 assert.equal(levels[1].plan.number,'CLI-P-PA');
 assert.deepEqual(levels[1].groups.map(g=>g.title),['2 · Colectores','R19 previo']);
 assert.equal(levels[0].groups[0].title,'Fichas · Serpentina');
 assert.deepEqual(others.map(g=>g.title),['Detalles','General']);
});
