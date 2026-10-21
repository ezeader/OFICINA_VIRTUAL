'use client';
import {useEffect,useRef} from 'react';
export default function CompassMark(){
 const ref=useRef<HTMLSpanElement>(null);
 useEffect(()=>{
  const reduced=matchMedia('(prefers-reduced-motion: reduce)');
  let frame=0,target=0,angle=0;
  const move=(e:PointerEvent)=>{if(e.pointerType==='touch'||reduced.matches)return;const b=ref.current?.getBoundingClientRect();if(!b)return;target=Math.atan2(e.clientY-b.top-b.height/2,e.clientX-b.left-b.width/2)*180/Math.PI-180;if(!frame)frame=requestAnimationFrame(tick)};
  const tick=()=>{const delta=((target-angle+540)%360)-180;angle+=delta*.12;if(ref.current)ref.current.style.setProperty('--compass-angle',`${angle}deg`);frame=Math.abs(delta)>.1?requestAnimationFrame(tick):0};
  window.addEventListener('pointermove',move,{passive:true});return()=>{window.removeEventListener('pointermove',move);cancelAnimationFrame(frame)};
 },[]);
 return <span ref={ref} className="compassMark" role="img" aria-label="La Brújula"><img src="/brand/ader-mark.webp" alt="" draggable={false}/></span>;
}
