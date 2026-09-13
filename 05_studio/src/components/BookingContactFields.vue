<script setup lang="ts">
import { ref } from 'vue';
import ContactMethodPicker from './ContactMethodPicker.vue';
import { words } from '../visit/copy';
import { bookingProfileCopy as copy,type ContactDetails } from '../booking-profile';
import { say } from '../state';
const props=withDefaults(defineProps<{modelValue:ContactDetails;disabled?:boolean;required?:boolean;nameLabel?:string}>(),{required:true});
const emit=defineEmits<{'update:modelValue':[ContactDetails]}>();
const nameInput=ref<HTMLInputElement>();
function change(key:keyof ContactDetails,value:string){emit('update:modelValue',{...props.modelValue,[key]:value});}
defineExpose({focus:()=>nameInput.value?.focus()});
</script>
<template>
 <div class="booking-contact-fields">
  <label>{{nameLabel||say(copy.name)}}<input ref="nameInput" :value="modelValue.name" @input="change('name',($event.target as HTMLInputElement).value)" autocomplete="name" :required="required" maxlength="80" :disabled="disabled"/></label>
  <div class="visit-contact-channel">
   <ContactMethodPicker :model-value="modelValue.contact_method" @update:model-value="change('contact_method',$event)" :disabled="disabled"/>
   <label class="visit-contact-value">{{say(modelValue.contact_method==='wechat'?words.wechat_id_7a6e86:modelValue.contact_method==='email'?words.email_address_a61e0e:modelValue.contact_method==='phone'?words.phone_number_15447d:words.contact_details_3b7403)}}<input :value="modelValue.contact" @input="change('contact',($event.target as HTMLInputElement).value)" :type="modelValue.contact_method==='email'?'email':modelValue.contact_method==='phone'?'tel':'text'" :autocomplete="modelValue.contact_method==='email'?'email':modelValue.contact_method==='phone'?'tel':'off'" :required="required" :minlength="modelValue.contact_method==='wechat'?1:3" maxlength="180" :disabled="disabled"/></label>
  </div>
 </div>
</template>
<style>
.booking-contact-fields{display:grid;gap:16px;min-width:0}.booking-contact-fields>label,.booking-contact-fields .visit-contact-value{display:grid;gap:8px;font-size:14px;min-width:0}.booking-contact-fields input:not([type=radio]){width:100%;min-width:0;min-height:48px;border:1px solid var(--line);border-radius:12px;padding:11px 13px;font:inherit;font-size:16px;background:var(--paper);color:var(--ink)}.booking-contact-fields input:not([type=radio]):focus-visible{outline:2px solid #66849a;outline-offset:-2px}.profile-contact .visit-contact-channel{display:grid;grid-template-columns:minmax(0,1fr);gap:12px;padding:0;border:0;background:transparent}.booking-profile-section{display:grid;gap:16px;border-top:1px solid var(--line);padding-top:20px;min-width:0}.booking-profile-section h3{margin:0;font-size:17px}.booking-profile-summary{display:flex;align-items:center;justify-content:space-between;gap:18px;padding:18px 0;min-width:0}.booking-profile-summary>div{display:grid;gap:7px;min-width:0;overflow-wrap:anywhere}.booking-profile-summary p{margin:0;color:var(--muted);font-size:14px;line-height:1.7}.booking-profile-summary button{display:inline-flex;align-items:center;gap:6px;min-height:44px;flex:none}.booking-profile-actions{display:flex;justify-content:flex-end;gap:14px}.profile-contact-error{margin:0;font-size:13px;color:var(--danger,#a74242)}
</style>
