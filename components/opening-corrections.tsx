'use client';
import {useState} from 'react';
import {CORRECTION_STATUS,correctionFor,fabricationMeasures,measureKey,parseLength,formatMeters,setCorrection,warningKey,itemProgress,type CorrectionStatus,type OpeningCorrection,type OpeningsReview,type ReviewItem} from '../lib/openings-review';

const statusClass=(s?:CorrectionStatus)=>'openingStatus '+(s||'open');
const when=(iso?:string)=>iso?new Date(iso).toLocaleString('es-AR',{dateStyle:'short',timeStyle:'short',timeZone:'America/Argentina/Buenos_Aires'}):'';

// Una fila editable: el valor de Revit queda fijo a la izquierda y la corrección se carga al lado.
function CorrectionEditor({entry,measure,disabled,onSave,onCancel}:{entry?:OpeningCorrection;measure:boolean;disabled:boolean;onSave:(patch:{value:string;note:string;status:CorrectionStatus})=>Promise<boolean>;onCancel?:()=>void}){
 const [value,setValue]=useState(entry?.value||''),[note,setNote]=useState(entry?.note||''),[status,setStatus]=useState<CorrectionStatus>(entry?.status||'open'),[saving,setSaving]=useState(false);
 const parsed=measure&&value.trim()?parseLength(value):null,invalid=measure&&!!value.trim()&&parsed==null;
 const nextStatus:CorrectionStatus=status==='open'&&(value.trim()||note.trim())?'proposed':status;
 const changed=value!==(entry?.value||'')||note!==(entry?.note||'')||nextStatus!==(entry?.status||'open');
 return <div className="openingCorrectionEditor">
  <label>{measure?'Medida corregida':'Valor o dato corregido'}<input value={value} disabled={disabled} maxLength={200} placeholder={measure?'Ej. 0,62 · 620 mm · 62 cm':'Ej. Aluminio anodizado, perfil 45 mm'} onChange={e=>setValue(e.target.value)}/>{measure&&value.trim()&&<small className={invalid?'openingWarning':''}>{invalid?'No se reconoce la medida. Usá m, cm o mm.':'Se registra como '+formatMeters(parsed!)}</small>}</label>
  <label>Nota para Revit<textarea rows={2} value={note} disabled={disabled} maxLength={2000} placeholder="Fuente, criterio o qué cambiar en la familia" onChange={e=>setNote(e.target.value)}/></label>
  <label>Estado<select value={nextStatus} disabled={disabled} onChange={e=>setStatus(e.target.value as CorrectionStatus)}>{(Object.keys(CORRECTION_STATUS) as CorrectionStatus[]).map(s=><option key={s} value={s}>{CORRECTION_STATUS[s]}</option>)}</select></label>
  <div className="openingCorrectionActions"><button className="primary" disabled={disabled||saving||!changed||invalid} onClick={async()=>{setSaving(true);const ok=await onSave({value,note,status:nextStatus});setSaving(false);if(ok)onCancel?.()}}>{saving?'Guardando…':'Guardar corrección'}</button>{onCancel&&<button onClick={onCancel}>Cancelar</button>}{entry?.updatedAt&&<small>Última edición {when(entry.updatedAt)}</small>}</div>
 </div>;
}

export default function OpeningCorrections({item,review,disabled,onSaveReview}:{item:ReviewItem;review?:OpeningsReview;disabled?:boolean;onSaveReview?:(next:OpeningsReview)=>Promise<boolean>}){
 const [editing,setEditing]=useState<string>();
 const readOnly=!onSaveReview,busy=readOnly||!!disabled,progress=itemProgress(item,review);
 const save=(key:string)=>async(patch:{value:string;note:string;status:CorrectionStatus})=>onSaveReview?onSaveReview(setCorrection(review,item.id,key,patch,new Date().toISOString())):false;
 const measures=fabricationMeasures(item);
 return <section className="openingCorrections" id={'opening-corrections-'+item.id} aria-label={'Revisión y correcciones de '+item.code}>
  <div className="openingCorrectionsHead"><div><p className="eyebrow">REVISIÓN · CORRECCIONES PARA REVIT</p><h5>Medidas y datos de {item.code}</h5></div><span>{progress.total?`${progress.total-progress.open} de ${progress.total} datos revisados`:'Sin advertencias en la lectura'}{progress.measures?` · ${progress.measures} medidas corregidas`:''}</span></div>
  <p className="openingHint">Los valores de Revit no se modifican desde acá. Cada corrección queda guardada en tu oficina, al lado del valor original, y figura como pendiente hasta aplicarla en Revit y volver a leer el modelo.{readOnly?' Esta vista es de solo lectura: abrí la oficina con sesión iniciada para cargar correcciones.':''}</p>
  <table className="openingMeasureTable"><thead><tr><th>Medida</th><th>Valor en Revit</th><th>Cota en la lámina</th><th>Corrección</th><th/></tr></thead><tbody>{measures.map(m=>{const key=measureKey(m.key),entry=correctionFor(review,item.id,key);return [<tr key={m.key} className={!m.value&&m.required?'missing':''}><th scope="row">{m.label}<small>{m.origin}</small>{m.note&&<small className="openingWarning">{m.note}</small>}</th><td>{m.value?m.value.replace('.',','):<b>Falta dato</b>}</td><td>{m.dimensioned?'Acotada':m.value?'Sin cota':'—'}</td><td>{entry?<><span className={statusClass(entry.status)}>{CORRECTION_STATUS[entry.status]}</span>{entry.value&&<strong>{entry.value}{m.key!=='panels'&&parseLength(entry.value)!=null&&!/^s*[d.,]+s*ms*$/.test(entry.value)?` = ${formatMeters(parseLength(entry.value)!)}`:''}</strong>}{entry.note&&<small>{entry.note}</small>}</>:<small>—</small>}</td><td>{!readOnly&&<button onClick={()=>setEditing(editing===key?undefined:key)} aria-expanded={editing===key}>{entry?'Editar':'Corregir'}</button>}</td></tr>,editing===key&&<tr key={m.key+'-edit'} className="openingEditRow"><td colSpan={5}><CorrectionEditor key={entry?.updatedAt||'new'} entry={entry} measure={!['panels','mullion','breakdown'].includes(m.key)} disabled={busy} onSave={save(key)} onCancel={()=>setEditing(undefined)}/></td></tr>]})}</tbody></table>
  {item.warnings.length>0&&<div className="openingWarningsList"><h6>{item.warnings.length} datos por revisar</h6>{item.warnings.map(w=>{const key=warningKey(w),entry=correctionFor(review,item.id,key);return <article key={key} className={'openingWarningCard '+(entry?.status||'open')}><div><span className={statusClass(entry?.status)}>{CORRECTION_STATUS[entry?.status||'open']}</span><p><small>Original de la lectura de Revit</small>{w}</p></div>{readOnly?(entry&&<p>{entry.value}{entry.note&&<small>{entry.note}</small>}</p>):<CorrectionEditor key={entry?.updatedAt||'new'} entry={entry} measure={false} disabled={busy} onSave={save(key)}/>}</article>})}</div>}
 </section>;
}
