<script setup lang="ts">
import { useId } from 'vue';
import { contentModule } from '../content-store';
import words from '../content/pages-Visit.json';
import { say } from '../state';
import type { ReservationPayload } from '../reservations';
type Method=ReservationPayload['contact_method'];
defineProps<{modelValue:Method;disabled?:boolean}>();
const emit=defineEmits<{'update:modelValue':[value:Method]}>();
const copy=contentModule('pages-Visit',words),name=useId();
const options=[{value:'wechat',key:'wechat_2941d2'},{value:'email',key:'email_b6d15f'},{value:'phone',key:'phone_ac7a62'},{value:'other',key:'another_way_f489b4'}] as const;
</script>
<template><fieldset class="contact-method-picker" :disabled="disabled"><legend>{{say(copy.contact_method_73d70a)}}</legend><div><label v-for="option in options" :key="option.value" :class="{selected:modelValue===option.value}"><input type="radio" :name="name" :value="option.value" :checked="modelValue===option.value" @change="emit('update:modelValue',option.value)"/><span>{{say(copy[option.key])}}</span></label></div></fieldset></template>
<style>
.contact-method-picker{border:0;padding:0;margin:0;min-width:0;}.contact-method-picker legend{font-size:13px;margin-bottom:9px;color:var(--ink);}.contact-method-picker>div{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:6px;padding:4px;border:1px solid #e2e8ec;border-radius:13px;background:#f5f7f9;}.contact-method-picker>div>label{position:relative;display:grid;place-items:center;min-height:44px;padding:8px 5px;text-align:center;font-size:13px;line-height:1.45;border:1px solid transparent;border-radius:9px;cursor:pointer;color:var(--muted);transition:background-color .3s var(--control-ease),border-color .3s var(--control-ease),color .3s var(--control-ease),box-shadow .3s var(--control-ease);}.contact-method-picker label.selected{background:#fff;border-color:#ccdce7;color:var(--ink);box-shadow:0 2px 5px #263b4d0a;}.contact-method-picker input[type=radio]{position:absolute;opacity:0;width:1px;height:1px;min-height:0;min-width:0;margin:0;padding:0;border:0;}.contact-method-picker label:has(input:focus-visible){outline:2px solid #617c91;outline-offset:2px;}.contact-method-picker:disabled label{cursor:default;opacity:.55;}.contact-method-picker span{overflow-wrap:anywhere;}
@media(hover:hover) and (pointer:fine){.contact-method-picker:not(:disabled) label:hover{background:#edf3f8;color:var(--ink);}}
</style>
