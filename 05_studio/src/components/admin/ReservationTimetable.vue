<script setup lang="ts">
import { computed,onBeforeUnmount,onMounted,ref,watch } from 'vue';
import { PhArrowLeft,PhArrowRight } from '@phosphor-icons/vue';
import { useDesk } from '../../admin';
import { contentModule } from '../../content-store';
import words from '../../content/reservation-timetable.json';
import { say,formatCopy,hamiltonDate,plusDays,prettyDate } from '../../state';
import InfoTip from '../InfoTip.vue';
const copy=contentModule('reservation-timetable',words),{request}=useDesk();
const props=defineProps<{active:boolean;refreshKey:number;selectedDate:string;selectedTime:string}>();
const emit=defineEmits<{select:[{date:string;at:string} ]}>();
type Slot={start:string;end:string;closed:boolean;blocked:boolean;pending:number;confirmed:number;completed:number};
type Day={date:string;open:string;close:string;closed:boolean;slots:Slot[]};
const first=ref(hamiltonDate()),days=ref<Day[]>([]),size=ref(7),offset=ref(0),busy=ref(false),error=ref(''),table=ref<HTMLElement>();
let seq=0,resize:ResizeObserver|undefined;
const visible=computed(()=>days.value.slice(offset.value,offset.value+size.value));
const rows=computed(()=>Array.from({length:48},(_,i)=>i).filter(i=>days.value.some(d=>!d.slots[i].closed||d.slots[i].pending+d.slots[i].confirmed+d.slots[i].completed>0)));
async function load(){const n=++seq;busy.value=true;error.value='';try{const data=await request<{days:Day[]}>(`/manage/reservation-timetable?start=${first.value}`);if(n===seq)days.value=data.days;}catch(e){if(n===seq)error.value=(e as Error).message;}finally{if(n===seq)busy.value=false;}}
function move(delta:number){const next=offset.value+delta*size.value;if(next>=0&&next<14)offset.value=next;else{first.value=plusDays(first.value,delta*7);offset.value=0;}}
function today(){offset.value=0;if(first.value===hamiltonDate())void load();else first.value=hamiltonDate();}
function label(day:Day,slot:Slot){return formatCopy(copy.slot,{v0:prettyDate(day.date),v1:slot.start+'–'+slot.end,v2:slot.confirmed,v3:slot.pending,v4:slot.completed});}
watch([()=>props.active,()=>props.refreshKey,first],()=>{if(props.active)void load();},{immediate:true});
onMounted(()=>{resize=new ResizeObserver(([entry])=>{size.value=entry.contentRect.width<420?3:entry.contentRect.width<720?4:7;offset.value=Math.min(offset.value,14-size.value);});if(table.value)resize.observe(table.value);});
onBeforeUnmount(()=>{seq++;resize?.disconnect();});
</script>
<template>
  <section ref="table" class="reservation-timetable">
    <header><div class="timetable-heading"><h2>{{say(copy.title)}}</h2><InfoTip :label="say(copy.help_label)"><p>{{say(copy.help)}}</p></InfoTip></div><div class="timetable-navigation"><button type="button" class="desk-icon-button" :aria-label="say(copy.previous)" :disabled="busy" @click="move(-1)"><PhArrowLeft/></button><button type="button" class="desk-link" @click="today">{{say(copy.today)}}</button><button type="button" class="desk-icon-button" :aria-label="say(copy.next)" :disabled="busy" @click="move(1)"><PhArrowRight/></button></div></header>
    <div class="timetable-legend"><span v-for="state in ['confirmed','pending','completed','closed']" :key="state" :class="state">{{say(copy[state as keyof typeof copy])}}</span></div>
    <p v-if="error" class="desk-error" role="alert">{{error}}</p><p v-if="busy&&!days.length" role="status">{{say(copy.loading)}}</p>
    <div v-if="visible.length" class="timetable-scroll" :aria-busy="busy">
      <div class="timetable-grid" :style="{'--days':visible.length}">
        <span class="timetable-date corner"/><strong v-for="day in visible" :key="day.date" class="timetable-date">{{prettyDate(day.date)}}</strong>
        <template v-for="index in rows" :key="index"><span class="timetable-time">{{days[0].slots[index].start}}</span><button v-for="day in visible" :key="day.date" type="button" class="timetable-slot" :class="{confirmed:day.slots[index].confirmed,pending:day.slots[index].pending,completed:day.slots[index].completed,closed:day.slots[index].closed||day.slots[index].blocked,selected:selectedDate===day.date&&selectedTime===day.slots[index].start}" :aria-label="label(day,day.slots[index])" :aria-pressed="selectedDate===day.date&&selectedTime===day.slots[index].start" @click="emit('select',{date:day.date,at:day.slots[index].start})"><span v-if="day.slots[index].confirmed" class="confirmed">{{formatCopy(copy.guests,{v0:day.slots[index].confirmed})}}</span><span v-if="day.slots[index].pending" class="pending">{{say(copy.pending)}} {{day.slots[index].pending}}</span><span v-if="day.slots[index].completed" class="completed">{{say(copy.completed)}} {{day.slots[index].completed}}</span><span v-if="!day.slots[index].pending&&!day.slots[index].confirmed&&!day.slots[index].completed" aria-hidden="true">{{day.slots[index].closed||day.slots[index].blocked?'—':'·'}}</span></button></template>
      </div>
    </div>
  </section>
</template>
