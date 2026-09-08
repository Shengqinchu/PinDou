<script setup lang="ts">
import { contentModule } from "../../content-store";
const copyText = contentModule("components-admin-ContentEditor", copyTextDefault);

import moduleNames from "../../content/data-editor-module-labels.json";
import copyTextDefault from "../../content/components-admin-ContentEditor.json";
import { say, locale } from "../../state";
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { PhArrowClockwise, PhImage, PhEye, PhUploadSimple, PhClockCounterClockwise } from "@phosphor-icons/vue";
import { useDesk } from "../../admin";
import { publishedModules, refreshContent, type MediaAsset } from "../../content-store";

const props=defineProps<{ active: boolean }>();
const { request }=useDesk();
type Data=Record<string,string[] | MediaAsset>;
type Doc={ name:string; version:number; published_version:number; data:Data; published:Data };
const items=ref<{name:string}[]>([]), name=ref('pages-Home'), doc=ref<Doc>(), search=ref('');
const busy=ref(false), error=ref(''), success=ref(''), device=ref('desktop'), tab=ref('edit');
const saved=ref('');
const drafts=new Map<string,Doc>();
const dirty=computed(()=>!!doc.value && JSON.stringify(doc.value.data)!==saved.value);
const revisions=ref<{id:number;version:number;action:string;data:Data;created_at:number}[]>([]);
const frame=ref<HTMLIFrameElement>();
const canvas=ref<HTMLElement>(), canvasWidth=ref(600);
const frameWidth=computed(()=>device.value==='desktop'?1280:390);
const frameScale=computed(()=>Math.max(.1,Math.min(1,(canvasWidth.value-24)/frameWidth.value)));
let previewResize:ResizeObserver|undefined;
let sequence=0, started=false;
const labels:Record<string,string>={ 'pages-Home':'home','pages-Visit':'visit','pages-Details':'details','pages-Shop':'shop','pages-Journal':'journal','pages-JournalEntry':'journal','pages-ReservationReceipt':'receipt','App':'navigation','media':'media' };
const words=copyText as Record<string,string[]>;
function label(n:string){return say((moduleNames as Record<string,string[]>)[n] || copyText.shared);}
const routes:Record<string,string>={'pages-Home':'/','pages-Visit':'/visit','pages-Details':'/details','pages-Shop':'/shop','pages-Journal':'/journal','pages-JournalEntry':'/journal','App':'/','media':'/'};
const previewRoute=computed(()=>`${routes[name.value] || '/'}?content-preview=1&preview-locale=${locale.value}`);
const fields=computed(()=>Object.entries(doc.value?.data || {}).filter(([key,value])=>!search.value || JSON.stringify(value).toLowerCase().includes(search.value.toLowerCase()) || key.toLowerCase().includes(search.value.toLowerCase())));
function mediaLabel(key:string){return say(words[({'hero-illustration':'hero','shop-collage':'collage','brand-zh':'brandZh','brand-en':'brandEn','brand-puppy':'puppy'} as Record<string,string>)[key] || (key.startsWith('space-')?'space':'photo')])+(/\d+$/.test(key)?` ${key.match(/\d+$/)?.[0]}`:'');}
function failure(e:unknown){error.value=(e as {status?:number}).status===409?say(copyText.conflict):(e as Error).message;}
async function load(force=false){
  const seq=++sequence;busy.value=true;error.value='';success.value='';
  try{
    const data=await request<Doc>('/manage/content/'+name.value);
    if(seq!==sequence)return;
    doc.value=!force&&drafts.has(name.value)?structuredClone(drafts.get(name.value)!):data;
    saved.value=JSON.stringify(data.data);sendPreview();
  }catch(e){if(seq===sequence)failure(e);}finally{if(seq===sequence)busy.value=false;}
}
async function choose(next:string){if(doc.value)drafts.set(doc.value.name,JSON.parse(JSON.stringify(doc.value)));name.value=next;search.value='';revisions.value=[];await load();}
async function save(publish=false){
  if(!doc.value||busy.value)return;busy.value=true;error.value='';success.value='';
  try{
    let next=await request<Doc>('/manage/content/'+name.value,{method:'PUT',body:JSON.stringify({version:doc.value.version,data:doc.value.data})});
    if(publish)next=await request<Doc>('/manage/content/'+name.value+'/publish',{method:'POST',body:JSON.stringify({version:next.version})});
    doc.value=next;saved.value=JSON.stringify(next.data);drafts.delete(name.value);
    success.value=say(publish?copyText.published:copyText.saved);await refreshContent();sendPreview();
  }catch(e){failure(e);}finally{busy.value=false;}
}
async function upload(key:string,event:Event){
  const input=event.target as HTMLInputElement,file=input.files?.[0];if(!file||!doc.value)return;
  busy.value=true;error.value='';success.value=say(copyText.uploading);
  try{const value=await request<MediaAsset>('/manage/media',{method:'POST',headers:{'Content-Type':file.type},body:file});doc.value.data[key]={src:value.src,width:value.width,height:value.height};success.value='';}
  catch(e){failure(e);success.value='';}finally{busy.value=false;input.value='';}
}
function sendPreview(){if(doc.value)frame.value?.contentWindow?.postMessage(JSON.parse(JSON.stringify({type:'studio-content-preview',modules:{...publishedModules.value,[doc.value.name]:doc.value.data}})),location.origin);}
const ready=(event:MessageEvent)=>{if(event.origin===location.origin&&event.source===frame.value?.contentWindow&&event.data?.type==='studio-preview-ready')sendPreview();};
async function history(){try{revisions.value=(await request<{items:typeof revisions.value}>('/manage/content/'+name.value+'/history')).items;}catch(e){failure(e);}}
function restore(data:Data){if(doc.value){doc.value.data=JSON.parse(JSON.stringify(data));success.value=say(copyText.restoreHelp);}}
watch(()=>props.active,async value=>{if(value&&!started){started=true;try{items.value=(await request<{items:{name:string}[]}>('/manage/content')).items.sort((a,b)=>(labels[b.name]?1:0)-(labels[a.name]?1:0));await load();}catch(e){failure(e);started=false;}}},{immediate:true});
watch(()=>doc.value?.data,()=>{void nextTick(sendPreview);},{deep:true});
onMounted(()=>{window.addEventListener('message',ready);previewResize=new ResizeObserver(entries=>{canvasWidth.value=entries[0].contentRect.width;});if(canvas.value)previewResize.observe(canvas.value);});
onBeforeUnmount(()=>{previewResize?.disconnect();sequence++;window.removeEventListener('message',ready);});
</script>
<template>
  <section class="studio-editor">
    <header class="desk-page-heading"><div><h1>{{say(copyText.title)}}</h1><p>{{say(copyText.intro)}}</p></div></header>
    <div class="editor-commandbar">
      <label class="field"><span>{{say(copyText.choose)}}</span><select :value="name" :disabled="busy" @change="choose(($event.target as HTMLSelectElement).value)"><option v-for="item in items" :key="item.name" :value="item.name">{{label(item.name)}}</option></select></label>
      <div class="editor-save-actions"><span class="editor-state">{{dirty?say(copyText.unsaved):success}}</span><button class="desk-button secondary" :disabled="busy||!doc" @click="save(false)">{{say(copyText.draft)}}</button><button class="desk-button primary" :disabled="busy||!doc" @click="save(true)">{{say(copyText.publish)}}</button></div>
    </div>
    <p v-if="error" role="alert" class="desk-error">{{error}} <button class="desk-link" :disabled="busy" @click="load(true)">{{say(copyText.reload)}}</button></p>
    <div class="editor-mobile-tabs"><button class="desk-button secondary" @click="tab='edit'">{{say(copyText.edit)}}</button><button class="desk-button secondary" @click="tab='preview'">{{say(copyText.preview)}}</button></div>
    <div class="editor-workspace" :data-tab="tab">
      <div class="editor-fields">
        <label class="field editor-search"><span>{{say(copyText.search)}}</span><input v-model="search" type="search" /></label>
        <p v-if="busy&&!doc">{{say(copyText.loading)}}</p>
        <template v-if="doc">
          <div v-for="([key,value],i) in fields" :key="key" class="editor-field-group">
            <template v-if="name==='rate-fields' && Array.isArray(value)"><label class="field"><span>{{say(words[key])}}</span><input type="number" min="0" max="99999" step="0.01" :value="value[0]" @input="value[0]=value[1]=($event.target as HTMLInputElement).value" /></label></template>
            <template v-else-if="Array.isArray(value)"><span class="editor-field-index">{{String(i+1).padStart(2,'0')}}</span><label class="field"><span>{{say(copyText.zh)}}</span><textarea v-model="value[0]" :rows="value[0].length>100?5:2" /></label><label class="field"><span>{{say(copyText.en)}}</span><textarea v-model="value[1]" :rows="value[1].length>180?5:2" /></label></template>
            <template v-else><h3>{{mediaLabel(key)}}</h3><img class="editor-image-preview" :src="value.src" :alt="mediaLabel(key)" loading="lazy" /><label class="editor-upload"><PhUploadSimple/>{{say(copyText.replace)}}<input type="file" accept="image/jpeg,image/png,image/webp" :disabled="busy" @change="upload(key,$event)" /></label><p class="form-help">{{say(copyText.imageHelp)}}</p></template>
          </div>
          <p v-if="!fields.length">{{say(copyText.empty)}}</p>
        </template>
        <button class="desk-button secondary" @click="history"><PhClockCounterClockwise/>{{say(copyText.history)}}</button>
        <div v-for="revision in revisions" :key="revision.id" class="editor-history-row"><span>{{new Date(revision.created_at*1000).toLocaleString()}} · v{{revision.version}}</span><button class="desk-link" @click="restore(revision.data)">{{say(copyText.restore)}}</button></div>
      </div>
      <aside class="editor-preview-pane">
        <div class="editor-preview-toolbar"><strong><PhEye/>{{say(copyText.preview)}}</strong><div><button :aria-pressed="device==='desktop'" @click="device='desktop'">{{say(copyText.desktop)}}</button><button :aria-pressed="device==='mobile'" @click="device='mobile'">{{say(copyText.mobile)}}</button></div></div>
        <div ref="canvas" class="editor-preview-canvas" :class="device"><iframe ref="frame" :style="{width:frameWidth+'px',height:(636/frameScale)+'px',transform:`scale(${frameScale})`,transformOrigin:'top left'}" :src="previewRoute" :title="say(copyText.preview)" @load="sendPreview" /></div>
        <p class="form-help">{{say(copyText.previewHelp)}}</p>
      </aside>
    </div>
  </section>
</template>
