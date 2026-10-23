import {env} from 'cloudflare:workers';
import manifest from '@/lib/document-assets.json';
import {uploadDocument} from '@/lib/document-storage.mjs';
export const dynamic='force-dynamic';
export const PUT=(request:Request)=>uploadDocument(request,env.BUCKET,manifest);
