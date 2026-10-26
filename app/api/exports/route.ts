import {env} from 'cloudflare:workers';
import {exportsRequest} from '@/lib/export-storage.mjs';
export const dynamic='force-dynamic';
export const GET=(request:Request)=>exportsRequest(request,env.BUCKET);
export const PUT=(request:Request)=>exportsRequest(request,env.BUCKET);
