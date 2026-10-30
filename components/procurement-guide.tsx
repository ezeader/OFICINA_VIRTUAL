'use client';
/** Tutorial compacto: una tarjeta chica que se prende con “Cómo se usa” y solo cambia de pestaña. */
export const guideSteps=[
 {tab:'Presupuesto por rubro',title:'Presupuesto por rubro',steps:['Es la planilla base de la obra: cada rubro con su subtotal y su peso en el total.','Se completa sola a medida que cargás precios o elegís un presupuesto.','“Hacer opcional” separa lo que el cliente decide después.']},
 {tab:'Cómputo',title:'Cómputo',steps:['Elegí el rubro arriba. Cada sistema se abre con sus ítems y cantidades, una sola vez cada uno.','Escribí la marca que querés pedir: para todo el sistema o ítem por ítem.','“Descargar Excel” arma la planilla para el proveedor con esas marcas.']},
 {tab:'Proveedores',title:'Proveedores',steps:['Listado por Pinamar y zona, costa atlántica y nacional.','Marcá “Apto” a quienes vas a pedirles precio.','“Gmail” abre el borrador del pedido (adjuntá el Excel y los planos); “WhatsApp” abre el texto. Al enviarlo, tocá el círculo: queda el tilde verde.','“Buscar en la zona” muestra comercios cercanos en el mapa.']},
 {tab:'Presupuestos',title:'Presupuestos',steps:['Arrastrá el Excel que devolvió el proveedor: se leen solos los precios, el alcance, la validez, los plazos y la zona.','Queda en el listado del rubro con el nombre del archivo. Tildá hasta 3 para compararlos lado a lado.','En Negociaciones registrás consultas, contraofertas y cómo baja el número.']},
];
export default function ProcurementGuide({step,onStep,onClose}:{step:number;onStep:(n:number)=>void;onClose:()=>void}){
 const s=guideSteps[step],last=step===guideSteps.length-1;
 return <aside className="pcGuide" aria-label="Cómo se usa"><header><small>{step+1} / {guideSteps.length}</small><b>{s.title}</b><button aria-label="Cerrar guía" onClick={onClose}>×</button></header>
  <ul>{s.steps.map(t=><li key={t}>{t}</li>)}</ul>
  <footer><button disabled={step===0} onClick={()=>onStep(step-1)}>←</button><button className="primary" onClick={()=>last?onClose():onStep(step+1)}>{last?'Listo':'Siguiente →'}</button></footer></aside>;
}
