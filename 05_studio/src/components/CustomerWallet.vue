<script setup lang="ts">
import { patchCopy } from '../patch-reservations';
import OfferLabel from '../visit/OfferLabel.vue';
import { reservationRevision,reservationStatus } from '../cancellation';
import { onBeforeUnmount,onMounted,ref,watch } from 'vue';
import { PhArrowClockwise,PhArrowRight } from '@phosphor-icons/vue';
import { walletCopy as copy,duration,type WalletDetail,type WalletCategory } from '../wallet';
import { accountCopy,accountUser,closeAccount } from '../account';
import { commerceApi,statusText } from '../commerce';
import { say,formatCopy,prettyDate } from '../state';
import type { Reservation } from '../reservations';
import WalletBalances from './WalletBalances.vue';
import WalletLedger from './WalletLedger.vue';
import ShopOrderHistory from './ShopOrderHistory.vue';
import { profileCopy } from '../profile';
const tab=ref<'wallet'|'bookings'|'orders'>('wallet'), category=ref<WalletCategory>('time'), page=ref(1), bookingPage=ref(1);
const data=ref<WalletDetail>(), bookings=ref<Reservation[]>([]), bookingTotal=ref(0), busy=ref(false), error=ref('');
const orderHistory=ref<{refresh:()=>Promise<void>;busy:boolean}|null>(null);
let sequence=0,timer:ReturnType<typeof setInterval>|undefined;
async function refresh(){
  const id=accountUser.value?.id;if(!id)return;
  const seq=++sequence;busy.value=true;error.value='';
  try{
    const [wallet,visits]=await Promise.all([commerceApi<WalletDetail>(`/auth/wallet?page=${page.value}&category=${category.value}`),commerceApi<{items:Reservation[];total:number}>(`/auth/reservations?page=${bookingPage.value}`)]);
    if(seq!==sequence||accountUser.value?.id!==id)return;
    data.value=wallet;bookings.value=visits.items;bookingTotal.value=visits.total;
  }catch(e){if(seq===sequence)error.value=(e as Error).message;}
  finally{if(seq===sequence)busy.value=false;}
}
function visibleRefresh(){if(document.visibilityState==='visible'&&!busy.value)void refresh();}
function refreshActive(){if(tab.value==='orders')void orderHistory.value?.refresh();else void refresh();}
watch(category,()=>{page.value=1;void refresh();});
watch([page,bookingPage],()=>void refresh());
watch(reservationRevision,()=>void refresh());
onMounted(()=>{void refresh();timer=setInterval(visibleRefresh,15000);window.addEventListener('focus',visibleRefresh);document.addEventListener('visibilitychange',visibleRefresh);});
onBeforeUnmount(()=>{sequence++;clearInterval(timer);window.removeEventListener('focus',visibleRefresh);document.removeEventListener('visibilitychange',visibleRefresh);});
</script>
<template>
  <div class="customer-wallet">
    <div class="wallet-toolbar"><div class="wallet-overview-tabs" role="group" :aria-label="say(accountCopy.account)"><button :aria-pressed="tab==='wallet'" @click="tab='wallet'">{{say(copy.account)}}</button><button :aria-pressed="tab==='bookings'" @click="tab='bookings'">{{say(accountCopy.my_reservations)}}</button><button :aria-pressed="tab==='orders'" @click="tab='orders'">{{say(accountCopy.my_orders)}}</button></div><button class="icon-button" :aria-label="say(copy.refresh)" :disabled="tab==='orders'?orderHistory?.busy:busy" @click="refreshActive"><PhArrowClockwise :size="19" :class="{spinning:tab==='orders'?orderHistory?.busy:busy}"/></button></div>
    <p v-if="error" class="form-error" role="alert">{{error}}</p><p v-if="busy&&!data" role="status">{{say(copy.loading)}}</p>
    <template v-if="data&&tab==='wallet'">
      <WalletBalances :account="data.account" customer/>
      <div class="wallet-history-tabs" role="group" :aria-label="say(copy.all_history)"><button :aria-pressed="category==='time'" @click="category='time'">{{say(copy.time_history)}}</button><button :aria-pressed="category==='points'" @click="category='points'">{{say(copy.point_history)}}</button></div>
      <WalletLedger v-if="data.entries.length" :entries="data.entries"/><p v-else class="wallet-empty">{{say(category==='time'?profileCopy.time_empty:profileCopy.points_empty)}}</p>
      <div v-if="data.total>30" class="wallet-pagination"><button :disabled="page===1||busy" @click="page--">{{say(copy.previous)}}</button><span>{{formatCopy(copy.page,{v0:page,v1:data.total})}}</span><button :disabled="page*30>=data.total||busy" @click="page++">{{say(copy.next)}}</button></div>
    </template>
    <template v-if="tab==='bookings'">
      <p v-if="!bookings.length&&!busy" class="account-note">{{say(accountCopy.no_reservations)}}</p>
      <ul class="account-bookings wallet-bookings"><li v-for="booking in bookings" :key="booking.id"><RouterLink :to="'/reservation/'+booking.id" @click="closeAccount"><span><strong>{{prettyDate(booking.booking.date)}}</strong><small>{{booking.booking.start}}–{{booking.booking.end}} · {{reservationStatus(booking.status)}}</small><small v-if="booking.booking.plan==='patch'">{{say(patchCopy.patch)}}</small><small v-if="booking.offer"><OfferLabel :offer="booking.offer"/></small><small>{{say(copy.booked)}} · {{duration(booking.booked_minutes)}}</small><small>{{say(copy.actual)}} · {{booking.actual_minutes==null?say(copy.unrecorded):formatCopy(copy.per_guest,{v0:duration(booking.actual_minutes),v1:booking.actual_guests||booking.booking.guests})}}</small><p v-if="booking.public_note">{{booking.public_note}}</p></span><PhArrowRight :size="18"/></RouterLink></li></ul>
      <div v-if="bookingTotal>30" class="wallet-pagination"><button :disabled="bookingPage===1||busy" @click="bookingPage--">{{say(copy.previous)}}</button><span>{{formatCopy(copy.page,{v0:bookingPage,v1:bookingTotal})}}</span><button :disabled="bookingPage*30>=bookingTotal||busy" @click="bookingPage++">{{say(copy.next)}}</button></div>
    </template>
    <ShopOrderHistory v-if="tab==='orders'" ref="orderHistory" :show-refresh="false"/>
  </div>
</template>
