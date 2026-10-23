'use client';
import {useState} from 'react';
export default function RevitOpenButton({id,label='Abrir esta tabla en Revit'}:{id:string;label?:string}){
 const [busy,setBusy]=useState(false),[message,setMessage]=useState('');
 async function open(){setBusy(true);setMessage('');try{const r=await fetch('http://127.0.0.1:18764/views/angel/open',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({viewId:id}),signal:AbortSignal.timeout(45000)});const d=await r.json() as {error?:string;message:string};if(!r.ok)throw Error(d.error);setMessage(d.message);}catch(e){setMessage(e instanceof TypeError?'Usá la PC con Revit y el conector local abiertos. La vista publicada sigue disponible aquí.':(e as Error).message)}finally{setBusy(false)}}
 return <span className="revitOpen"><button disabled={busy} onClick={open}>{busy?'Abriendo…':label+' ↗'}</button>{message&&<small role="status">{message}</small>}</span>;
}

