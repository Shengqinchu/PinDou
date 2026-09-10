<script setup lang="ts">
import { computed,onBeforeUnmount,onMounted,ref,watch } from 'vue';
import { PhArrowLeft,PhArrowRight } from '@phosphor-icons/vue';
import { useDesk } from '../../admin';
import { contentModule } from '../../content-store';
import words from '../../content/reservation-timetable.json';
import { say,formatCopy,hamiltonDate,plusDays,prettyDate } from '../../state';
import InfoTip from '../InfoTip.vue';
import ReservationHoursNote from '../ReservationHoursNote.vue';
import endWords from '../../content/visit-flow.json';
import { layoutBookings,type TimetableBooking,type PlacedBooking } from '../../timetable-layout';
import { minutes } from '../../reservations';
const endCopy=contentModule('visit-flow',endWords);
const copy=contentModule('reservation-timetable',words),{request}=useDesk();
const props=defineProps<{active:boolean;refreshKey:number;selectedDate:string;selectedTime:string}>();
const emit=defineEmits<{select:[{date:string;at:string} ];inspect:[id:string]}>();
type Slot={start:string;end:string;closed:boolean;blocked:boolean;pending:number;confirmed:number;completed:number};
type Day={date:string;open:string;close:string;closed:boolean;slots:Slot[];bookings:TimetableBooking[]};
const first=ref(hamiltonDate()),days=ref<Day[]>([]),size=ref(7),offset=ref(0),busy=ref(false),error=ref(''),table=ref<HTMLElement>();
let seq=0,resize:ResizeObserver|undefined;
const visible=computed(()=>days.value.slice(offset.value,offset.value+size.value));
const rows=computed(()=>{const active=Array.from({length:48},(_,i)=>i).filter(i=>days.value.some(d=>!d.slots[i].closed||d.slots[i].pending+d.slots[i].confirmed+d.slots[i].completed>0));return active.length?Array.from({length:active.at(-1)!-active[0]+1},(_,i)=>active[0]+i):[];});
const groups=computed(()=>Object.fromEntries(visible.value.map(day=>[day.date,layoutBookings(day.bookings||[])])));
function blockStyle(booking:PlacedBooking){return {'--start':minutes(booking.start)/30-(rows.value[0]||0),'--length':(minutes(booking.end)-minutes(booking.start))/30,left:`calc(${booking.lane/booking.columns*100}% + 3px)`,width:`calc(${100/booking.columns}% - 6px)`,'--tone':String((booking.lane*137+booking.id.charCodeAt(booking.id.length-1)*11)%360)};}
function bookingLabel(booking:PlacedBooking){return [booking.name,booking.note,formatCopy(copy.guests,{v0:booking.guests}),booking.start+'–'+booking.end,say(copy[booking.status])].filter(Boolean).join(' · ');}
const endBoundary=computed(()=>{const last=rows.value.at(-1);return last===undefined?'':days.value[0]?.slots[last]?.end||'';});
async function load(){const n=++seq;busy.value=true;error.value='';try{const data=await request<{days:Day[]}>(`/manage/reservation-timetable?start=${first.value}`);if(n===seq)days.value=data.days;}catch(e){if(n===seq)error.value=(e as Error).message;}finally{if(n===seq)busy.value=false;}}
function move(delta:number){const next=offset.value+delta*size.value;if(next>=0&&next<14)offset.value=next;else{first.value=plusDays(first.value,delta*7);offset.value=0;}}
function today(){offset.value=0;if(first.value===hamiltonDate())void load();else first.value=hamiltonDate();}
function label(day:Day,slot:Slot){return formatCopy(copy.slot,{v0:prettyDate(day.date),v1:slot.start+'–'+slot.end,v2:slot.confirmed,v3:slot.pending,v4:slot.completed});}
watch([()=>props.active,()=>props.refreshKey,first],()=>{if(props.active)void load();},{immediate:true});
onMounted(()=>{resize=new ResizeObserver(([entry])=>{size.value=entry.contentRect.width<460?1:entry.contentRect.width<720?2:entry.contentRect.width<1050?3:entry.contentRect.width<1350?4:7;offset.value=Math.min(offset.value,14-size.value);});if(table.value)resize.observe(table.value);});
onBeforeUnmount(()=>{seq++;resize?.disconnect();});
</script>
<template>
  <section ref="table" class="reservation-timetable">
    <header><div class="timetable-heading"><h2>{{say(copy.title)}}</h2><InfoTip :label="say(copy.help_label)"><p>{{say(copy.help)}}</p></InfoTip></div><div class="timetable-navigation"><button type="button" class="desk-icon-button" :aria-label="say(copy.previous)" :disabled="busy" @click="move(-1)"><PhArrowLeft/></button><button type="button" class="desk-link" @click="today">{{say(copy.today)}}</button><button type="button" class="desk-icon-button" :aria-label="say(copy.next)" :disabled="busy" @click="move(1)"><PhArrowRight/></button></div></header>
    <div class="timetable-legend"><span v-for="state in ['confirmed','pending','completed','closed']" :key="state" :class="state">{{say(copy[state as keyof typeof copy])}}</span></div>
    <p v-if="error" class="desk-error" role="alert">{{error}}</p><p v-if="busy&&!days.length" role="status">{{say(copy.loading)}}</p>
    <div v-if="visible.length&&rows.length" class="timetable-scroll" :aria-busy="busy">
      <div class="timetable-grid" :style="{'--days':visible.length,gridTemplateRows:`48px repeat(${rows.length},var(--slot-height)) 30px`}">
        <span class="timetable-date corner"/><strong v-for="day in visible" :key="day.date" class="timetable-date">{{prettyDate(day.date)}}</strong>
        <span v-for="(index,row) in rows" :key="index" class="timetable-time" :style="{gridColumn:1,gridRow:row+2}">{{days[0].slots[index].start}}</span>
        <div v-for="(day,column) in visible" :key="day.date" class="timetable-day" :style="{gridColumn:column+2,gridRow:`2 / span ${rows.length}`}">
          <button v-for="index in rows" :key="index" type="button" class="timetable-slot" :class="{closed:day.slots[index].closed||day.slots[index].blocked,selected:selectedDate===day.date&&selectedTime===day.slots[index].start}" :aria-label="label(day,day.slots[index])" :aria-pressed="selectedDate===day.date&&selectedTime===day.slots[index].start" @click="emit('select',{date:day.date,at:day.slots[index].start})"/>
          <div class="timetable-events"><button v-for="booking in groups[day.date]" :key="booking.id" type="button" class="timetable-booking" :style="blockStyle(booking)" :aria-label="bookingLabel(booking)" :title="bookingLabel(booking)" @click="emit('inspect',booking.id)"><span class="timetable-booking-content"><strong>{{booking.name||booking.id}}</strong><span v-if="booking.note" class="timetable-booking-note">{{booking.note}}</span><span>{{formatCopy(copy.guests,{v0:booking.guests})}}</span><small>{{booking.start}}–{{booking.end}}</small><small class="timetable-booking-status" :class="booking.status">{{say(copy[booking.status])}}</small></span></button></div>
        </div>
        <template v-if="endBoundary"><span class="timetable-time timetable-end-boundary">{{endBoundary}}</span><span v-for="day in visible" :key="'end-'+day.date" class="timetable-end-cell">{{!day.closed&&day.close===endBoundary?say(endCopy.end_marker):'—'}}</span></template>
      </div>
    </div>
    <ReservationHoursNote/>
  </section>
</template>
