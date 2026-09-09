<script setup lang="ts">
import { contentModule } from "../../content-store";
const copyText = contentModule("components-admin-JournalEditor", copyTextDefault);

import MediaUpload from "./MediaUpload.vue";
import EditorDiagnostics from "./EditorDiagnostics.vue";
import uploadCopy from "../../content/components-admin-ContentEditor.json";
import { uploadMedia } from "../../editor";
import { useJournalImport } from "../../journal-import";
import FlagText from "../FlagText.vue";
import copyTextDefault from "../../content/components-admin-JournalEditor.json";
import { say, tr, hamiltonDate } from "../../state";
import { computed, onBeforeUnmount, ref, watch } from "vue";
import { PhArrowUp, PhArrowDown, PhPlus, PhX, PhArrowSquareOut } from "@phosphor-icons/vue";
import { useDesk } from "../../admin";
import { journalSource, refreshJournal, type JournalPost, type JournalPhoto } from "../../journal";
const props=defineProps<{active:boolean}>();
const {request}=useDesk();
type Entry={id:string;data:JournalPost;version:number;published:boolean;has_changes?:boolean};
const items=ref<Entry[]>([]), selected=ref<Entry>(), share=ref(''), busy=ref(false), error=ref(''), success=ref(''), preview=ref(false),uploading=ref(false);
const originals=new Map<string,Entry>();
let started=false;
function failure(e:unknown){const issue=e as {status?:number;requestId?:string;name:string;message:string};error.value=issue.name==='AbortError'?say(uploadCopy.uploadTimeout):issue.status===409?say(copyText.conflict):issue.message;if(issue.requestId)error.value+=' · '+say(uploadCopy.requestId)+' '+issue.requestId;}
async function load(){try{items.value=(await request<{items:Entry[]}>('/manage/journal')).items;}catch(e){failure(e);}}
function choose(entry:Entry){if(selected.value)originals.set(selected.value.id,JSON.parse(JSON.stringify(selected.value)));selected.value=JSON.parse(JSON.stringify(originals.get(entry.id)||entry));error.value='';success.value='';preview.value=false;}
function create(){choose({id:'story-'+crypto.randomUUID().slice(0,12),version:0,published:false,data:{id:'',title:say(copyText.emptyTitle),title_en:'',body:'',body_en:'',date:hamiltonDate(),source:'',kind:'full',images:[]}});selected.value!.data.id=selected.value!.id;}
const importer=useJournalImport<Entry>(request,async result=>{await load();choose(result);share.value='';});
const importBusy=importer.running,importProgress=importer.progress,importError=importer.error;
watch(importBusy,value=>{busy.value=value;},{flush:'sync'});
async function importPost(){if(!busy.value&&!importBusy.value&&share.value.trim())await importer.start(share.value);}
async function save(publish=false){if(!selected.value||busy.value)return;busy.value=true;error.value='';success.value='';try{
  const data=await request<{version:number}>('/manage/journal/'+selected.value.id,{method:'PUT',body:JSON.stringify({version:selected.value.version,data:selected.value.data})});selected.value.version=data.version;
  if(publish){const live=await request<{version:number}>('/manage/journal/'+selected.value.id+'/publish',{method:'POST',body:JSON.stringify({version:data.version})});selected.value.version=live.version;selected.value.published=true;}
  originals.delete(selected.value.id);success.value=say(publish?copyText.published:copyText.saved);await load();await refreshJournal();
}catch(e){failure(e);}finally{busy.value=false;}}
async function unpublish(){if(!selected.value||busy.value)return;busy.value=true;error.value='';try{const result=await request<{version:number}>('/manage/journal/'+selected.value.id+'/unpublish',{method:'POST',body:JSON.stringify({version:selected.value.version})});selected.value.version=result.version;selected.value.published=false;await load();await refreshJournal();}catch(e){failure(e);}finally{busy.value=false;}}
async function upload(files:File[]){if(!selected.value||!files.length||busy.value)return;busy.value=true;uploading.value=true;error.value='';try{for(const file of files){if(selected.value.data.images.length>=40)break;const image=await uploadMedia(request,file,true);selected.value.data.images.push(image);}}catch(e){failure(e);}finally{busy.value=false;uploading.value=false;}}
function move(index:number,delta:number){const photos=selected.value?.data.images;if(!photos||index+delta<0||index+delta>=photos.length)return;const [photo]=photos.splice(index,1);photos.splice(index+delta,0,photo);}
async function translate(){if(!selected.value||busy.value)return;busy.value=true;error.value='';success.value=say(copyText.translating);try{const result=await request<{title_en:string;body_en:string}>('/manage/journal-translate',{method:'POST',body:JSON.stringify({title:selected.value.data.title,body:selected.value.data.body})});selected.value.data.title_en=result.title_en;selected.value.data.body_en=result.body_en;success.value=say(copyText.translationReview);}catch(e){failure(e);success.value='';}finally{busy.value=false;}}
watch(()=>props.active,v=>{if(v&&!started){started=true;void load();}},{immediate:true});
</script>
<template>
  <section class="studio-editor">
    <header class="desk-page-heading"><div><h1>{{say(copyText.title)}}</h1><p>{{say(copyText.intro)}}</p></div></header>
    <form class="journal-import-bar" @submit.prevent="importPost"><label class="field"><span>{{say(copyText.link)}}</span><input v-model="share" type="text" :disabled="busy||importBusy" /></label><button class="desk-button primary" :disabled="busy||importBusy||!share.trim()">{{say(copyText.import)}}</button><button type="button" class="desk-button secondary" :disabled="busy" @click="create"><PhPlus/>{{say(copyText.new)}}</button></form>
    <p v-if="importProgress" role="status" class="editor-state">{{importProgress}}</p><p v-if="importError" role="alert" class="desk-error">{{importError}}</p>
    <p v-if="error" role="alert" class="desk-error">{{error}}</p><p v-if="success" role="status" class="editor-state">{{success}}</p>
    <div class="journal-editor-workspace">
      <aside class="journal-editor-list"><button v-for="item in items" :key="item.id" :class="{selected:selected?.id===item.id}" :disabled="busy" @click="choose(item)"><img v-if="item.data.images[0]" :src="journalSource(item.data.images[0].src)" alt="" loading="lazy"/><span><small>{{item.data.date}} · {{say(item.published?copyText.live:copyText.draft)}}</small><strong><FlagText :text="tr(item.data.title,item.data.title_en||item.data.title)" /></strong></span></button><button class="desk-link" :disabled="busy" @click="load">{{say(copyText.retry)}}</button></aside>
      <div v-if="selected" class="journal-editor-form">
        <div class="journal-editor-toolbar"><button class="desk-button secondary" :aria-pressed="preview" @click="preview=!preview">{{say(preview?copyText.edit:copyText.preview)}}</button><button class="desk-button secondary" :disabled="busy" @click="save(false)">{{say(copyText.save)}}</button><button class="desk-button primary" :disabled="busy" @click="save(true)">{{say(copyText.publish)}}</button></div>
        <div v-if="preview" class="journal-editor-reading"><time>{{selected.data.date}}</time><h2><FlagText :text="tr(selected.data.title,selected.data.title_en)" /></h2><p>{{tr(selected.data.body,selected.data.body_en)}}</p><img v-for="photo in selected.data.images" :key="photo.src" :src="journalSource(photo.src)" :alt="selected.data.title" :width="photo.width" :height="photo.height" loading="lazy" /></div>
        <template v-else>
          <div class="editor-pair"><label class="field"><span>{{say(copyText.date)}}</span><input v-model="selected.data.date" type="date" /></label><label class="field"><span>{{say(copyText.source)}}</span><input v-model="selected.data.source" type="url" /></label></div>
          <div class="editor-pair"><label class="field"><span>{{say(copyText.titleZh)}}</span><textarea v-model="selected.data.title" rows="2" /></label><label class="field"><span>{{say(copyText.titleEn)}}</span><textarea v-model="selected.data.title_en" rows="2" /></label></div>
          <div class="editor-pair"><label class="field"><span>{{say(copyText.bodyZh)}}</span><textarea v-model="selected.data.body" rows="14" /></label><label class="field"><span>{{say(copyText.bodyEn)}}</span><textarea v-model="selected.data.body_en" rows="14" /></label></div>
          <button class="desk-button secondary" :disabled="busy||!selected.data.body" @click="translate">{{say(copyText.translate)}}</button>
          <h2>{{say(copyText.photos)}} · {{selected.data.images.length}}</h2><p class="form-help">{{say(copyText.photoHelp)}}</p>
          <div class="journal-editor-photos"><figure v-for="(photo,i) in selected.data.images" :key="photo.src+'-'+i"><img :src="journalSource(photo.src)" :alt="selected.data.title+' '+(i+1)" loading="lazy"/><figcaption><span>{{i+1}}</span><button class="desk-icon-button" :disabled="i===0" :aria-label="say(copyText.previous)" @click="move(i,-1)"><PhArrowUp/></button><button class="desk-icon-button" :disabled="i===selected.data.images.length-1" :aria-label="say(copyText.next)" @click="move(i,1)"><PhArrowDown/></button><button class="desk-icon-button" :aria-label="say(copyText.remove)" @click="selected.data.images.splice(i,1)"><PhX/></button></figcaption></figure></div>
          <MediaUpload :disabled="busy" :busy="uploading" multiple original :label="say(copyText.add)" :status="error?{error:true,text:error}:undefined" @select="upload" />
          <button v-if="selected.published" class="desk-link journal-unpublish" :disabled="busy" @click="unpublish">{{say(copyText.unpublish)}}</button>
        </template>
      </div>
      <p v-else class="editor-empty">{{say(copyText.choose)}}</p>
    </div>
    <EditorDiagnostics />
  </section>
</template>
