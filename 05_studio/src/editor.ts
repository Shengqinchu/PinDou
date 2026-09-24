// Authoring state lives outside the template. Files, versions and preview state
// are scoped to the captured document, never whichever page happens to be active.
import { computed, onBeforeUnmount, ref, watch } from "vue";
import { type MediaAsset, refreshContent } from "./content-store";
import uploadWords from "./content/data-commerce-messages.json";
import editorWords from "./content/components-admin-ContentEditor.json";
import { CommerceError } from "./commerce";
import { say } from "./state";
export type EditorData = Record<string, string[] | MediaAsset>;
export type EditorDocument = { name:string; version:number; published_version:number; data:EditorData; published:EditorData };
export type EditorRequest = <T>(path:string,init?:RequestInit)=>Promise<T>;
type Words = Record<string,string[]>;
const clone = <T>(value:T):T => JSON.parse(JSON.stringify(value));

export function useContentEditor(request:EditorRequest,words:Words) {
  const items=ref<{name:string}[]>([]),name=ref('pages-Home'),doc=ref<EditorDocument>(),search=ref('');
  const busy=ref(false),error=ref(''),success=ref(''),saved=ref('');
  const uploadKey=ref(''),uploadStatus=ref<Record<string,{error:boolean;text:string}>>({});
  const drafts=new Map<string,EditorDocument>();
  const draftStorage='puppy-studio-editor-drafts-v1';
  // Static website copy only. Keep unfinished edits across a release reload;
  // never silently replace a newer server version with a recovered document.
  try {
    const stored=JSON.parse(sessionStorage.getItem(draftStorage)||'[]');
    if(Array.isArray(stored))for(const [key,value] of stored){
      if(typeof key==='string'&&value?.name===key&&Number.isInteger(value.version)&&value.data&&value.published)drafts.set(key,value);
    }
  } catch {}
  function persistDrafts(){try{sessionStorage.setItem(draftStorage,JSON.stringify([...drafts]));}catch{}}
  const dirty=computed(()=>!!doc.value&&JSON.stringify(doc.value.data)!==saved.value);
  const revisions=ref<{id:number;version:number;action:string;data:EditorData;created_at:number}[]>([]);
  const globalQuery=ref(''),matches=ref<{name:string;key:string;value:string[]}[]>([]),searching=ref(false);
  let sequence=0,searchSequence=0,searchTimer:ReturnType<typeof setTimeout>;
  function failure(e:unknown) {
    const issue=e as CommerceError;
    const message=issue.name==='AbortError'?say(words.uploadTimeout):issue.status===409?say(words.conflict):issue.message;
    error.value=message+(issue.requestId?` · ${say(words.requestId)} ${issue.requestId}`:'');
  }
  async function load(force=false) {
    const selected=name.value,seq=++sequence;busy.value=true;error.value='';success.value='';
    try {
      const data=await request<EditorDocument>('/manage/content/'+selected);
      if(seq!==sequence)return;
      doc.value=!force&&drafts.has(selected)?clone(drafts.get(selected)!):data;
      saved.value=JSON.stringify(data.data);
      if(!force&&drafts.has(selected)&&doc.value.version!==data.version) error.value=say(words.conflict);
    } catch(e) {if(seq===sequence)failure(e);} finally {if(seq===sequence)busy.value=false;}
  }
  async function choose(next:string,key='') {
    if(busy.value)return;
    if(doc.value){
      if(dirty.value)drafts.set(doc.value.name,clone(doc.value));else drafts.delete(doc.value.name);
      persistDrafts();
    }
    name.value=next;search.value=key;revisions.value=[];await load();
  }
  async function initialize() {
    try {items.value=(await request<{items:{name:string}[]}>('/manage/content')).items;await load();}
    catch(e){failure(e);}
  }
  async function save(publish=false) {
    if(!doc.value||busy.value)return;
    const current=doc.value;busy.value=true;error.value='';success.value='';
    try {
      const next=await request<EditorDocument>('/manage/content/'+current.name,{method:'PUT',body:JSON.stringify({version:current.version,data:current.data,publish})});
      doc.value=next;saved.value=JSON.stringify(next.data);drafts.delete(current.name);
      persistDrafts();
      success.value=say(publish?words.published:words.saved);uploadStatus.value={};
      if(publish)await refreshContent();
    } catch(e){failure(e);} finally{busy.value=false;}
  }
  async function upload(key:string,file:File) {
    if(!doc.value||busy.value)return;
    const current=doc.value;busy.value=true;uploadKey.value=key;error.value='';success.value='';
    uploadStatus.value[key]={error:false,text:say(words.uploading)};
    try {
      const value=await uploadMedia(request,file);
      current.data[key]={src:value.src,width:value.width,height:value.height};
      uploadStatus.value[key]={error:false,text:say(words.uploaded)};
    } catch(e){failure(e);uploadStatus.value[key]={error:true,text:error.value};}
    finally{busy.value=false;uploadKey.value='';}
  }
  async function history(){try{revisions.value=(await request<{items:typeof revisions.value}>('/manage/content/'+name.value+'/history')).items;}catch(e){failure(e);}}
  function restore(data:EditorData){if(doc.value&&!busy.value){doc.value.data=clone(data);success.value=say(words.restoreHelp);}}
  function exportDraft() {
    if(!doc.value)return;
    const url=URL.createObjectURL(new Blob([JSON.stringify(doc.value,null,2)],{type:'application/json'}));
    const a=document.createElement('a');a.href=url;a.download=`pindou-${doc.value.name}-draft.json`;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
  }
  watch(globalQuery,value=>{
    clearTimeout(searchTimer);const seq=++searchSequence;
    if(value.trim().length<2){matches.value=[];searching.value=false;return;}
    searching.value=true;
    searchTimer=setTimeout(async()=>{try{const result=await request<{items:typeof matches.value}>('/manage/content-search?q='+encodeURIComponent(value));if(seq===searchSequence)matches.value=result.items;}catch(e){if(seq===searchSequence)failure(e);}finally{if(seq===searchSequence)searching.value=false;}},280);
  });
  watch(()=>doc.value?.data,()=>{
    if(!doc.value||busy.value)return;
    if(dirty.value)drafts.set(doc.value.name,clone(doc.value));else drafts.delete(doc.value.name);
    persistDrafts();
  },{deep:true,flush:'post'});
  onBeforeUnmount(()=>{sequence++;searchSequence++;clearTimeout(searchTimer);});
  return {items,name,doc,search,busy,error,success,dirty,revisions,uploadKey,uploadStatus,globalQuery,matches,searching,failure,load,choose,initialize,save,upload,history,restore,exportDraft};
}

export async function uploadMedia(request:EditorRequest,file:File,original=false):Promise<MediaAsset> {
  if(file.size>12*1024*1024)throw new CommerceError(say(uploadWords.image_too_large),413,'image_too_large');
  async function send<T>(path:string,init:RequestInit,attempts=1):Promise<T>{
    let failure:unknown;
    for(let attempt=0;attempt<attempts;attempt++){
      const abort=new AbortController(),timer=setTimeout(()=>abort.abort(),45000);
      try{return await request<T>(path,{...init,signal:abort.signal});}
      catch(error){
        failure=error;
        const issue=error as CommerceError;
        if(attempt===attempts-1||!(issue.name==='AbortError'||issue.status===0||issue.status>=500))break;
      }finally{clearTimeout(timer);}
    }
    if((failure as Error)?.name==='AbortError')throw new CommerceError(say(editorWords.uploadTimeout),0,'upload_timeout');
    throw failure;
  }
  // The production tunnel times out on a slow, single large request. Small,
  // idempotent chunks retain the original bytes and allow safe retries.
  if(file.size<=512*1024)return send<MediaAsset>('/manage/media'+(original?'?original=true':''),{method:'POST',headers:{'Content-Type':file.type||'application/octet-stream'},body:file});
  const id=crypto.randomUUID().replaceAll('-',''),size=256*1024;
  const chunks=Math.ceil(file.size/size);
  for(let index=0;index<chunks;index++){
    await send(`/manage/media/chunks/${id}/${index}`,{method:'PUT',headers:{'Content-Type':'application/octet-stream'},body:file.slice(index*size,(index+1)*size)},3);
  }
  return send<MediaAsset>(`/manage/media/chunks/${id}/complete?size=${file.size}&chunks=${chunks}&original=${original}`,{method:'POST'},3);
}
