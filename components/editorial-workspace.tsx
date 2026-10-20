'use client';
import {useState,useEffect,useRef} from 'react';
import {X,ArrowUpRight} from 'lucide-react';
import inventory from '../data/urbetrack.json';
const local='http://127.0.0.1:18763/';
export default function EditorialWorkspace({id,onClose}:{id:string,onClose:()=>void}){
 const [loaded,setLoaded]=useState(false),[delayed,setDelayed]=useState(false); const frame=useRef<HTMLIFrameElement>(null);
 useEffect(()=>{function status(e:MessageEvent){if(e.origin==='http://127.0.0.1:18763'&&e.source===frame.current?.contentWindow&&e.data?.type==='ader-editor-ready')setLoaded(true)}window.addEventListener('message',status);return()=>window.removeEventListener('message',status)},[]);
 useEffect(()=>{const t=setTimeout(()=>setDelayed(true),7000);return()=>clearTimeout(t)},[]);
 const url=local+'Storyboard_Urbetrack_R01.html?video='+encodeURIComponent(id)+'&view=montage&theme=ader';
 const video=inventory.videos.find(v=>v.id===id);
 return <div className="editorWorkspace" role="dialog" aria-modal="true" aria-label="Mesa editorial integrada"><div className="editorWorkspaceBar"><div><img src="/brand/ader-mark.webp" alt="Ader Studio"/><span><small>ADER STUDIO / MESA EDITORIAL</small><strong>{id} · {video?.title}</strong></span></div><div><a href={url} target="_blank" rel="noreferrer" title="Abrir en otra pestaña"><ArrowUpRight size={18}/></a><button aria-label="Cerrar mesa editorial" onClick={onClose}><X size={21}/></button></div></div><div className="editorConnection"><span className={loaded?'ready':''}/>{loaded?'Servicio local · las decisiones se guardan en el proyecto original':'Conectando con el editor de esta computadora…'}<a href="/Iniciar_Urbetrack.ps1" download>Iniciar editor</a></div>{delayed&&!loaded&&<div className="editorFallback"><img src="/brand/ader-mark.webp" alt=""/><h2>Tu mesa editorial, en esta computadora.</h2><p>El navegador todavía no pudo conectarse al editor dentro de la oficina. Podés abrirlo con la misma visual de Ader Studio en una pestaña local.</p><a className="msPrimary" href={url} target="_blank" rel="noreferrer">Abrir mesa editorial local <ArrowUpRight size={16}/></a><small>Conserva el proyecto, los comentarios y el historial originales.</small></div>}<iframe ref={frame} title={'Mesa editorial '+id} src={url} referrerPolicy="origin" allow="microphone; local-network-access http://127.0.0.1:18763; loopback-network http://127.0.0.1:18763"/></div>
}



