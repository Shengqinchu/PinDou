<script setup lang="ts">
import { computed } from 'vue';
import { reservationEditCopy as copy } from '../reservation-edit';
import { say } from '../state';
import { clock, type ReservationBooking } from '../reservations';
const props=defineProps<{modelValue:ReservationBooking;disabled?:boolean}>();
const emit=defineEmits<{ 'update:modelValue':[ReservationBooking] }>();
const times=computed(()=>Array.from({length:48},(_,index)=>clock(index*30)));
function update(key:keyof ReservationBooking,value:string|number){emit('update:modelValue',{...props.modelValue,[key]:value});}
</script>
<template>
 <fieldset class="reservation-edit-fields" :disabled="disabled">
  <legend>{{say(copy.admin_title)}}</legend>
  <label class="desk-field">{{say(copy.date)}}<input :value="modelValue.date" :aria-label="say(copy.date)" type="date" required @input="update('date',($event.target as HTMLInputElement).value)"/></label>
  <label class="desk-field">{{say(copy.guests)}}<input :value="modelValue.guests" :aria-label="say(copy.guests)" type="number" inputmode="numeric" min="1" max="99" step="1" required @input="update('guests',Number(($event.target as HTMLInputElement).value))"/></label>
  <label class="desk-field">{{say(copy.start)}}<select :value="modelValue.start" :aria-label="say(copy.start)" @change="update('start',($event.target as HTMLSelectElement).value)"><option v-for="time in times" :key="time" :value="time">{{time}}</option></select></label>
  <label class="desk-field">{{say(copy.end)}}<select :value="modelValue.end" :aria-label="say(copy.end)" :disabled="disabled||modelValue.plan==='patch'" @change="update('end',($event.target as HTMLSelectElement).value)"><option v-for="time in times" :key="time" :value="time">{{time}}</option></select></label>
  <p class="fine-print">{{say(copy.admin_help)}}</p>
 </fieldset>
</template>
<style scoped>
.reservation-edit-fields{border:0;padding:0;margin:24px 0;display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:16px;min-width:0;width:100%;max-width:100%;box-sizing:border-box}
.reservation-edit-fields legend{font-size:18px;font-weight:500;margin-bottom:16px}
.reservation-edit-fields p{grid-column:1/-1;margin:0;line-height:1.6}
.reservation-edit-fields .desk-field{min-width:0}.reservation-edit-fields input,.reservation-edit-fields select{font-size:16px;min-height:44px;width:100%;max-width:100%;min-width:0;box-sizing:border-box}
@media(max-width:360px){.reservation-edit-fields{gap:12px}}
</style>
