<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { PhEye, PhClockCounterClockwise } from "@phosphor-icons/vue";
import { contentModule, publishedModules } from "../../content-store";
import defaults from "../../content/components-admin-ContentEditor.json";
import moduleNames from "../../content/data-editor-module-labels.json";
import carousel from "../../content/data-components-StudioCarousel-photos.json";
import { say, locale } from "../../state";
import { useDesk } from "../../admin";
import { useContentEditor } from "../../editor";
import MediaUpload from "./MediaUpload.vue";
import EditorDiagnostics from "./EditorDiagnostics.vue";
const copyText=contentModule('components-admin-ContentEditor',defaults);
const props=defineProps<{active:boolean}>();
const {request}=useDesk();
const {items,name,doc,search,busy,error,success,dirty,revisions,uploadStatus,uploadKey,globalQuery,matches,searching,load,choose,initialize,save,upload,history,restore,exportDraft}=useContentEditor(request,copyText);
const device=ref('desktop'),tab=ref('edit'),mediaChoice=ref('hero-illustration');
const frame=ref<HTMLIFrameElement>(),canvas=ref<HTMLElement>(),canvasWidth=ref(600),canvasHeight=ref(560);
const frameWidth=computed(()=>device.value==='desktop'?1280:390);
const frameScale=computed(()=>Math.max(.1,Math.min(1,(canvasWidth.value-24)/frameWidth.value)));
let observer:ResizeObserver|undefined,started=false;
const words=copyText as Record<string,string[]>;
const shortcuts=['pages-Home','pages-Visit','pages-Details','pages-Journal','App','media'];
function label(n:string){return say((moduleNames as Record<string,string[]>)[n]||copyText.shared);}
const routes:Record<string,string>={'pages-Home':'/','pages-Visit':'/visit','pages-Details':'/details','components-BeadingProcess':'/details','pages-Shop':'/shop','pages-Journal':'/journal','pages-JournalEntry':'/journal','App':'/','media':'/'};
const previewReload=ref(0),previewStatus=ref<'connecting'|'synced'|'error'>('connecting'),previewStale=ref(false);
let previewRevision=0,previewTimeout:ReturnType<typeof setTimeout>;
const previewRoute=computed(()=>{
  const path=routes[name.value]||'/',query=`content-preview=1&preview-locale=${locale.value}&preview-refresh=${previewReload.value}`;
  return import.meta.env.DEV?`${path}?${query}`:`/studio-api/site?preview-path=${encodeURIComponent(path)}&${query}`;
});
const matchingFields=computed(()=>Object.entries(doc.value?.data||{}).filter(([key])=>!(name.value==='pages-Visit'&&key==='label_1efc6a')).filter(([key,value])=>!search.value||JSON.stringify(value).toLowerCase().includes(search.value.toLowerCase())||key.toLowerCase().includes(search.value.toLowerCase())).sort(([a],[b])=>{
  if(name.value!=='media')return 0;
  const order=(k:string)=>k.startsWith('space-')?10+carousel.findIndex(p=>p.image===k):['hero-illustration','shop-collage','brand-zh','brand-en','brand-en-contact','brand-puppy','owner-avatar','arrival-entrance','parking-entrance','parking-location'].indexOf(k);
  return order(a)-order(b);
}));
const fields=computed(()=>name.value==='media'?matchingFields.value.filter(([key])=>key===mediaChoice.value):matchingFields.value);
function mediaLabel(key:string){
  if(key.startsWith('space-'))return say(copyText.space)+' '+String(carousel.findIndex(p=>p.image===key)+1).padStart(2,'0');
  if(key.startsWith('process-'))return say(copyText.processPhoto)+' '+key.replace('process-','');
  const mapped=({'hero-illustration':'hero','shop-collage':'collage','brand-zh':'brandZh','brand-en':'brandEn','brand-en-contact':'brandEnContact','brand-puppy':'puppy','owner-avatar':'avatar','arrival-entrance':'arrivalEntrance','parking-entrance':'parkingEntrance','parking-location':'parkingLocation'} as Record<string,string>)[key];
  return say(words[mapped||'photo'])+(mapped?'':' · '+key);
}
function sendPreview(){
  if(!doc.value||!frame.value?.contentWindow)return;
  previewStatus.value='connecting';clearTimeout(previewTimeout);
  try { frame.value.contentWindow.postMessage(JSON.parse(JSON.stringify({type:'studio-content-preview',revision:++previewRevision,module:doc.value.name,modules:{...publishedModules.value,[doc.value.name]:doc.value.data}})),location.origin); }
  catch {previewStatus.value='error';return;}
  previewTimeout=setTimeout(()=>previewStatus.value='error',4000);
}
const ready=(event:MessageEvent)=>{
  if(event.origin!==location.origin||event.source!==frame.value?.contentWindow)return;
  if(event.data?.type==='studio-preview-ready'){previewStale.value=!!event.data.build&&event.data.build!==__STUDIO_BUILD__;sendPreview();}
  if(event.data?.type==='studio-preview-applied'&&event.data.revision===previewRevision&&event.data.module===doc.value?.name){clearTimeout(previewTimeout);previewStatus.value='synced';}
};
function reconnectPreview(){previewStatus.value='connecting';previewReload.value++;}
watch(()=>props.active,value=>{if(value&&!started){started=true;void initialize();}},{immediate:true});
watch(()=>doc.value?.data,()=>void nextTick(sendPreview),{deep:true});
onMounted(()=>{window.addEventListener('message',ready);observer=new ResizeObserver(([entry])=>{canvasWidth.value=entry.contentRect.width+24;canvasHeight.value=entry.contentRect.height;});if(canvas.value)observer.observe(canvas.value);});
onBeforeUnmount(()=>{observer?.disconnect();clearTimeout(previewTimeout);window.removeEventListener('message',ready);});
</script>
<template>
  <section class="studio-editor">
    <header class="desk-page-heading"><div><h1>{{say(copyText.title)}}</h1><p>{{say(copyText.intro)}}</p></div></header>
    <div class="editor-global-search"><label class="field"><span>{{say(copyText.searchAll)}}</span><input v-model="globalQuery" type="search" :placeholder="say(copyText.searchAllHelp)" /></label><p v-if="searching" role="status">{{say(copyText.loading)}}</p><div v-else-if="matches.length" class="editor-search-results"><button v-for="match in matches" :key="match.name+match.key" :disabled="busy" @click="choose(match.name,match.key)"><small>{{label(match.name)}}</small><span>{{say(match.value)}}</span></button></div><p v-else-if="globalQuery.trim().length>1" role="status">{{say(copyText.empty)}}</p></div>
    <nav class="editor-page-shortcuts" :aria-label="say(copyText.choose)"><button v-for="page in shortcuts" :key="page" :disabled="busy" :aria-pressed="name===page" @click="choose(page)">{{label(page)}}</button></nav>
    <div class="editor-commandbar">
      <label class="field"><span>{{say(copyText.choose)}}</span><select :value="name" :disabled="busy" @change="choose(($event.target as HTMLSelectElement).value)"><option v-for="item in items" :key="item.name" :value="item.name">{{label(item.name)}}</option></select></label>
      <div class="editor-save-actions"><span class="editor-state" role="status">{{busy?say(copyText.working):(success||(dirty?say(copyText.unsaved):''))}}</span><button class="desk-button secondary" :disabled="busy||!doc" @click="save(false)">{{say(copyText.draft)}}</button><button class="desk-button primary" :disabled="busy||!doc" @click="save(true)">{{say(copyText.publish)}}</button></div>
    </div>
    <p v-if="error" role="alert" class="desk-error">{{error}} <button class="desk-link" @click="exportDraft">{{say(copyText.exportDraft)}}</button> <button class="desk-link" :disabled="busy" @click="load(true)">{{say(copyText.reload)}}</button></p>
    <div class="editor-mobile-tabs"><button class="desk-button secondary" @click="tab='edit'">{{say(copyText.edit)}}</button><button class="desk-button secondary" @click="tab='preview'">{{say(copyText.preview)}}</button></div>
    <div class="editor-workspace" :data-tab="tab">
      <div class="editor-fields">
        <div v-if="name==='media'" class="editor-media-picker"><button v-for="([key,value]) in matchingFields" :key="key" :disabled="busy" :aria-pressed="mediaChoice===key" :title="mediaLabel(key)" @click="mediaChoice=key"><img v-if="!Array.isArray(value)" :src="value.src" alt="" loading="lazy"/><span>{{mediaLabel(key)}}</span></button></div>
        <label class="field editor-search"><span>{{say(copyText.search)}}</span><input v-model="search" type="search" /></label>
        <p v-if="busy&&!doc">{{say(copyText.loading)}}</p>
        <template v-if="doc">
          <fieldset v-for="([key,value],i) in fields" :key="key" :data-content-key="key" class="editor-field-group" :disabled="busy">
            <template v-if="name==='rate-fields' && Array.isArray(value)"><label class="field"><span>{{say(words[key])}}</span><input type="number" min="0" max="99999" step="0.01" :value="value[0]" @input="value[0]=value[1]=($event.target as HTMLInputElement).value" /></label></template>
            <template v-else-if="Array.isArray(value)"><span class="editor-field-index">{{String(i+1).padStart(2,'0')}}</span><label class="field"><span>{{say(copyText.zh)}}</span><textarea v-model="value[0]" :rows="value[0].length>100?5:2" /></label><label class="field"><span>{{say(copyText.en)}}</span><textarea v-model="value[1]" :rows="value[1].length>180?5:2" /></label><p v-if="name==='pages-Visit'&&key==='make_from_your_chosen_arrival_until_37196a'" class="editor-field-help">{{say(copyText.schedulePlaceholder)}} <RouterLink to="/manage?view=reservation-calendar">{{say(copyText.editSchedule)}}</RouterLink></p></template>
            <template v-else><h3>{{mediaLabel(key)}}</h3><img class="editor-image-preview" :src="value.src" :alt="mediaLabel(key)" loading="lazy" /><MediaUpload :disabled="busy" :busy="uploadKey===key" :status="uploadStatus[key]" @select="files=>upload(key,files[0])" /></template>
          </fieldset>
          <p v-if="!fields.length">{{say(copyText.empty)}}</p>
        </template>
        <button class="desk-button secondary" @click="history"><PhClockCounterClockwise/>{{say(copyText.history)}}</button>
        <div v-for="revision in revisions" :key="revision.id" class="editor-history-row"><span>{{new Date(revision.created_at*1000).toLocaleString()}} · v{{revision.version}}</span><button class="desk-link" @click="restore(revision.data)">{{say(copyText.restore)}}</button></div>
      </div>
      <aside class="editor-preview-pane">
        <div class="editor-preview-toolbar"><strong><PhEye/>{{say(copyText.preview)}}</strong><div><button :aria-pressed="device==='desktop'" @click="device='desktop'">{{say(copyText.desktop)}}</button><button :aria-pressed="device==='mobile'" @click="device='mobile'">{{say(copyText.mobile)}}</button></div></div>
        <div ref="canvas" class="editor-preview-canvas" :class="device"><iframe ref="frame" :style="{width:frameWidth+'px',height:(Math.max(100,canvasHeight)/frameScale)+'px',transform:`scale(${frameScale})`,transformOrigin:'top left'}" :src="previewRoute" :title="say(copyText.preview)" @load="sendPreview" /></div>
        <div class="editor-preview-state" :data-state="previewStatus" role="status"><span>{{say(previewStatus==='synced'?copyText.previewSynced:previewStatus==='error'?copyText.previewDisconnected:copyText.previewConnecting)}}</span><button v-if="previewStatus==='error'" class="desk-link" @click="reconnectPreview">{{say(copyText.reconnectPreview)}}</button></div>
        <p v-if="previewStale" class="editor-field-help">{{say(copyText.previewNewVersion)}}</p>
        <p class="form-help">{{say(copyText.previewHelp)}}</p><p class="editor-field-help">{{say(copyText.previewConditional)}}</p>
      </aside>
    </div>
    <EditorDiagnostics />
  </section>
</template>
