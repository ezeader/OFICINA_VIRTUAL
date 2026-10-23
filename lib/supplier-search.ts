import type {Supplier} from './procurement';
type Candidate={id:string;name:string;address:string;contact:string;source:string;lat?:number;lon?:number;trades?:string[];kind?:string;trusted?:boolean;savedId?:string};
const norm=(s:string)=>s.normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase().replace(/[^a-z0-9]/g,'');
export function mergeCandidates(candidates:Candidate[],suppliers:Supplier[]):Candidate[]{
 const out:Candidate[]=[];
 for(const c of candidates){
  if(out.some(o=>o.id===c.id||(norm(o.name)===norm(c.name)&&norm(o.address)===norm(c.address))))continue;
  const saved=suppliers.find(s=>s.id===c.savedId||s.sourceId===c.id||(norm(s.name)===norm(c.name)&&norm(s.zone)===norm(c.address)));
  out.push({...c,trusted:saved?.trusted??false,savedId:saved?.id});
 }
 return out;
}
