import {env} from 'cloudflare:workers';
import manifest from '@/lib/document-assets.json';
import {readDocument} from '@/lib/document-storage.mjs';
export const dynamic='force-dynamic';
export const GET=(request:Request)=>readDocument(request,env.BUCKET,manifest);
export const HEAD=GET;
