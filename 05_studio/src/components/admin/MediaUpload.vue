<script setup lang="ts">
import { ref } from "vue";
import { PhUploadSimple, PhSpinnerGap } from "@phosphor-icons/vue";
import { contentModule } from "../../content-store";
import defaults from "../../content/components-admin-ContentEditor.json";
import { say } from "../../state";
const words=contentModule('components-admin-ContentEditor',defaults);
const props=defineProps<{disabled?:boolean;busy?:boolean;multiple?:boolean;original?:boolean;label?:string;help?:string;status?:{error:boolean;text:string}}>();
const emit=defineEmits<{select:[files:File[]]}>();
const input=ref<HTMLInputElement>();
function pick(event:Event){const element=event.target as HTMLInputElement;const files=Array.from(element.files||[]);element.value='';if(files.length)emit('select',files);}
</script>
<template>
  <div class="media-upload" :aria-busy="busy">
    <button type="button" class="desk-button secondary media-upload-button" :disabled="disabled" @click="input?.click()"><PhSpinnerGap v-if="busy" class="spinning"/><PhUploadSimple v-else/>{{busy?say(words.uploading):(label||say(words.replace))}}</button>
    <input ref="input" hidden type="file" :accept="original?'image/jpeg,image/png,image/webp':'.jpg,.jpeg,.png,.webp,.avif,.bmp'" :multiple="multiple" :disabled="disabled" @change="pick" />
    <p class="form-help">{{help||say(original?words.originalImageHelp:words.imageHelp)}}</p>
    <p v-if="status" :role="status.error?'alert':'status'" :class="['media-upload-status',{'is-error':status.error}]">{{status.text}}</p>
  </div>
</template>
