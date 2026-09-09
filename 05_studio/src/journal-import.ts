import { ref,onBeforeUnmount,onMounted } from 'vue';
import { contentModule } from './content-store';
import errorsDefault from './content/data-commerce-messages.json';
import copyDefault from './content/components-admin-JournalEditor.json';
import { say } from './state';
import type { EditorRequest } from './editor';
const messages=contentModule('data-commerce-messages',errorsDefault) as Record<string,string[]>;
const words=contentModule('components-admin-JournalEditor',copyDefault);
const storageKey='puppy-studio-import-job';
export function useJournalImport<T>(request:EditorRequest,complete:(result:T)=>Promise<void>) {
  const running=ref(false),progress=ref(''),error=ref('');
  let timer:ReturnType<typeof setTimeout>,id='',stopped=false;
  function clear(){id='';try{sessionStorage.removeItem(storageKey);}catch{}running.value=false;}
  async function poll(){
    if(!id||stopped)return;
    try{
      const job=await request<{status:string;completed:number;total:number;result?:T;error?:string}>('/manage/journal-import-jobs/'+id);
      if(job.status==='done'&&job.result){clear();progress.value='';await complete(job.result);return;}
      if(job.status==='failed'){clear();progress.value='';error.value=say(messages[job.error||'']||messages.import_source_unavailable);return;}
      progress.value=job.total?`${say(words.importPhotos)} ${job.completed} / ${job.total}`:say(words.importing);
    }catch(e){error.value=(e as Error).message;if((e as {status?:number}).status===404){clear();return;}}
    if(id&&!stopped)timer=setTimeout(poll,1800);
  }
  async function start(share:string){
    if(running.value)return;running.value=true;error.value='';progress.value=say(words.importing);
    try{const result=await request<{id:string}>('/manage/journal-import-jobs',{method:'POST',body:JSON.stringify({share})});id=result.id;try{sessionStorage.setItem(storageKey,id);}catch{}await poll();}
    catch(e){clear();progress.value='';error.value=(e as Error).message;}
  }
  onMounted(()=>{try{id=sessionStorage.getItem(storageKey)||'';}catch{}if(id){running.value=true;void poll();}});
  onBeforeUnmount(()=>{stopped=true;clearTimeout(timer);});
  return {running,progress,error,start};
}
