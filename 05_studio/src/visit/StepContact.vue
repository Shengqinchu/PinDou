<script setup lang="ts">
import LiftTitle from '../components/LiftTitle.vue';
import { nextTick,ref } from 'vue';
import { PhPencilSimple } from '@phosphor-icons/vue';
import { say,formatCopy,prettyDate } from '../state';
import { copy,words,guestCount } from './copy';
import BookingContactFields from '../components/BookingContactFields.vue';
import { bookingProfileCopy as profileCopy,contactMethodLabel } from '../booking-profile';
import MoneyText from '../components/MoneyText.vue';
import NotificationPreferences from '../components/NotificationPreferences.vue';
import type { VisitFlow } from './useVisitFlow';
const props=defineProps<{flow:VisitFlow}>();
const fields=ref<InstanceType<typeof BookingContactFields>>();
async function edit(){props.flow.beginDetailsEdit();await nextTick();fields.value?.focus();}
</script>
<template>
 <div class="visit-stage-title"><LiftTitle as="h2" :text="say(copy.contact)"/></div>
 <div class="visit-review"><div><small>{{say(copy.step_experience)}}</small><strong>{{say(flow.offer?.label||(flow.draft.booking.plan==='day'?words.a_day_of_making_01d6e2:words.by_the_hour_5300b2))}}<MoneyText v-if="flow.offer" :text="flow.offer.currency+' '+flow.offer.amount"/></strong><button type="button" :disabled="flow.locked" @click="flow.navigate(0)"><PhPencilSimple/>{{say(copy.edit)}}</button></div><div><small>{{say(copy.step_time)}}</small><strong>{{guestCount(flow.draft.booking.guests)}} · {{prettyDate(flow.draft.booking.date)}} · {{flow.draft.booking.start}}–{{flow.draft.booking.end}}</strong><button type="button" :disabled="flow.locked" @click="flow.navigate(1)"><PhPencilSimple/>{{say(copy.edit)}}</button></div></div>
 <p v-if="flow.contactLoading&&!flow.attempt" class="form-help" role="status">{{say(profileCopy.loading)}}</p>
 <p v-if="flow.contactError" class="form-error" role="alert">{{flow.contactError}} <button type="button" class="text-link" @click="flow.loadContactContext()">{{say(profileCopy.retry)}}</button></p>
 <div v-if="flow.savedDetails&&!flow.attempt" class="booking-profile-summary visit-saved-contact" role="group" :aria-label="say(profileCopy.title)"><div><strong>{{flow.draft.name}}</strong><p>{{contactMethodLabel(flow.draft.contact_method)}} · {{flow.draft.contact}}</p></div><button type="button" :disabled="flow.locked||flow.contactLoading" @click="edit"><PhPencilSimple/>{{say(copy.edit)}}</button></div>
 <template v-else-if="!flow.contactLoading||flow.attempt"><BookingContactFields ref="fields" class="visit-contact" :model-value="flow.draft" @update:model-value="flow.editDetails" :name-label="say(words.guest_name_e468f6)" :disabled="flow.locked"/><button v-if="flow.contactProfile?.complete&&!flow.attempt" type="button" class="text-link visit-contact-cancel" :disabled="flow.locked" @click="flow.useSavedDetails()">{{say(profileCopy.cancel)}}</button></template>
 <details class="visit-notes"><summary>{{say(words.anything_you_would_like_us_to_know_eef3ab)}}</summary><textarea v-model="flow.draft.notes" :aria-label="say(words.anything_you_would_like_us_to_know_eef3ab)" rows="2" maxlength="1500"/></details>
 <p class="visit-confirmation-note">{{say(copy.confirmation_note)}}</p>
 <NotificationPreferences compact :method="flow.draft.contact_method" :contact="flow.draft.contact"/>
</template>
