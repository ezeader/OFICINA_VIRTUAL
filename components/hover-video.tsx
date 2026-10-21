'use client';
import {useRef,useState} from 'react';
import {Play} from 'lucide-react';

export default function HoverVideo({id,title,onOpen}:{id:string,title:string,onOpen:()=>void}){
 const video=useRef<HTMLVideoElement>(null),active=useRef(false);
 const [loaded,setLoaded]=useState(false),[playing,setPlaying]=useState(false);
 function start(){
  if(window.matchMedia('(prefers-reduced-motion: reduce)').matches)return;
  active.current=true;setLoaded(true);
  if(video.current)void video.current.play().catch(()=>setPlaying(false));
 }
 function stop(){active.current=false;setPlaying(false);if(video.current){video.current.pause();video.current.currentTime=0;}}
 return <button className={'msVideoCover realPreview hoverVideo'+(playing?' isPlaying':'')} aria-label={'Previsualizar '+id+' '+title} onPointerEnter={e=>{if(e.pointerType==='mouse')start()}} onPointerLeave={stop} onFocus={start} onBlur={stop} onClick={onOpen}>
  <img src={'/urbetrack-previews/'+id+'.jpg'} alt={'Fotograma de '+title} loading="lazy"/>
  {loaded&&<video ref={video} src={'/urbetrack-previews/'+id+'.mp4'} muted autoPlay loop playsInline preload="metadata" aria-hidden="true" onLoadedData={()=>{if(active.current)void video.current?.play().catch(()=>setPlaying(false));}} onPlaying={()=>{if(active.current)setPlaying(true);else stop();}} onError={()=>setPlaying(false)}/>}
  <span className="previewCode">{id} / URBETRACK</span><span className="msCoverPlay"><Play size={20}/></span>
 </button>
}
