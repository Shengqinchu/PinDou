<script setup lang="ts">
import { ref } from 'vue';
import { useDesk } from '../../admin';
import { say } from '../../state';
import { contentModule } from '../../content-store';
import defaults from '../../content/components-admin-ContentEditor.json';
const copy=contentModule('components-admin-ContentEditor',defaults),{request}=useDesk();
type Event={request_id:string;created_at:number;route:string;method:string;status:number;elapsed_ms:number;code:string};
const events=ref<Event[]>([]),busy=ref(false),state=ref(''),error=ref('');
async function load(){if(busy.value)return;busy.value=true;error.value='';try{const result=await request<{status:string;events:Event[]}>('/manage/diagnostics');events.value=result.events;state.value=result.status;}catch(e){error.value=(e as Error).message;}finally{busy.value=false;}}
</script>
<template>
  <details class="editor-diagnostics" @toggle="($event.target as HTMLDetailsElement).open&&load()"><summary>{{say(copy.diagnostics)}}</summary><div class="editor-diagnostics-heading"><p v-if="state==='ok'" role="status">{{say(copy.healthy)}}</p><button class="desk-button secondary" :disabled="busy" @click="load">{{say(copy.refresh)}}</button></div><p>{{say(copy.diagnosticsHelp)}}</p><p v-if="error" role="alert">{{error}}</p><div class="editor-diagnostics-events"><div v-for="event in events" :key="event.request_id"><time>{{new Date(event.created_at*1000).toLocaleTimeString()}}</time><span>{{event.method}} {{event.route}}</span><strong :class="{failed:event.status>=400}">{{event.status}}</strong><span>{{event.elapsed_ms}} ms</span><code>{{event.code||event.request_id}}</code></div></div></details>
</template>
