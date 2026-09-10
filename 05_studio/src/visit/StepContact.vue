<script setup lang="ts">
import LiftTitle from '../components/LiftTitle.vue';
import { useId } from 'vue';
import { PhPencilSimple } from '@phosphor-icons/vue';
import { say,formatCopy,prettyDate } from '../state';
import { copy,words,guestCount } from './copy';
import ContactMethodPicker from '../components/ContactMethodPicker.vue';
import MoneyText from '../components/MoneyText.vue';
import type { VisitFlow } from './useVisitFlow';
defineProps<{flow:VisitFlow}>();
const helpId=useId();
</script>
<template>
 <div class="visit-stage-title"><LiftTitle as="h2" :text="say(copy.contact)"/></div>
 <div class="visit-review"><div><small>{{say(copy.step_experience)}}</small><strong>{{say(flow.offer?.label||(flow.draft.booking.plan==='day'?words.a_day_of_making_01d6e2:words.by_the_hour_5300b2))}}<MoneyText v-if="flow.offer" :text="flow.offer.currency+' '+flow.offer.amount"/></strong><button type="button" :disabled="flow.locked" @click="flow.navigate(0)"><PhPencilSimple/>{{say(copy.edit)}}</button></div><div><small>{{say(copy.step_time)}}</small><strong>{{guestCount(flow.draft.booking.guests)}} · {{prettyDate(flow.draft.booking.date)}} · {{flow.draft.booking.start}}–{{flow.draft.booking.end}}</strong><button type="button" :disabled="flow.locked" @click="flow.navigate(1)"><PhPencilSimple/>{{say(copy.edit)}}</button></div></div>
 <p :id="helpId" class="visit-returning-help">{{say(copy.returning_help)}}</p>
 <div class="visit-contact"><label>{{say(words.guest_name_e468f6)}}<input v-model.trim="flow.draft.name" autocomplete="name" :required="!flow.canOmitDetails" :aria-describedby="helpId" maxlength="80"/></label><div class="visit-contact-channel"><ContactMethodPicker v-model="flow.draft.contact_method" :disabled="flow.locked"/><label class="visit-contact-value">{{say(flow.draft.contact_method==='wechat'?words.wechat_id_7a6e86:flow.draft.contact_method==='email'?words.email_address_a61e0e:flow.draft.contact_method==='phone'?words.phone_number_15447d:words.contact_details_3b7403)}}<input v-model.trim="flow.draft.contact" :type="flow.draft.contact_method==='email'?'email':flow.draft.contact_method==='phone'?'tel':'text'" :autocomplete="flow.draft.contact_method==='email'?'email':flow.draft.contact_method==='phone'?'tel':'off'" :required="!flow.canOmitDetails" :aria-describedby="helpId" minlength="3" maxlength="180"/></label></div></div>
 <details class="visit-notes"><summary>{{say(words.anything_you_would_like_us_to_know_eef3ab)}}</summary><textarea v-model="flow.draft.notes" :aria-label="say(words.anything_you_would_like_us_to_know_eef3ab)" rows="2" maxlength="1500"/></details>
 <p class="visit-confirmation-note">{{say(copy.confirmation_note)}}</p>
</template>
