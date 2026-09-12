<script setup lang="ts">
import { computed, ref, watch } from 'vue';
import StudioGlyph from './StudioGlyph.vue';
import { studioWords,fillWords } from '../utils/studio-content';
import { chooseCell,minutes,shortDate,type Booking,type Calendar,type Slot } from '../utils/studio-booking';
defineOptions({options:{styleIsolation:'shared'}});
const props=defineProps<{calendar:Calendar;booking:Booking;disabled:boolean;language:string;width:number}>();
const emit=defineEmits<{select:[Booking]}>();
const offset=ref(0),choosingEnd=ref(false),message=ref(false);
const count=computed(()=>props.width>=520?4:3),days=computed(()=>props.calendar.days.slice(offset.value,offset.value+count.value));
const rows=computed(()=>props.calendar.days[0]?.slots.map((slot,index)=>({time:slot.start,index}))||[]);
const end=computed(()=>props.calendar.days[0]?.slots.slice(-1)[0]?.end||'');
const text=(key:string)=>studioWords('calendar',key)[props.language==='en'?1:0];
function capacityLabel(slot:Slot){return slot.buffered?text('full_buffer'):slot.capacity_full?text('full'):slot.low_capacity?fillWords(studioWords('calendar','remaining_seats'),props.language,{v0:slot.remaining_seats!}):'';}
function selected(date:string,time:string){return date===props.booking.date&&minutes(time)>=minutes(props.booking.start)&&minutes(time)<minutes(props.booking.end);}
function choose(di:number,ri:number){
  if(props.disabled)return;
  const day=days.value[di],slot=day.slots[ri];
  const result=chooseCell(props.calendar,props.booking,day,slot,choosingEnd.value);
  if(!result){message.value=true;return;}
  choosingEnd.value=result.choosingEnd;message.value=false;emit('select',result.booking);
}
function page(delta:number){offset.value=Math.max(0,Math.min(Math.floor((props.calendar.days.length-1)/count.value)*count.value,offset.value+delta*count.value));}
function help(){uni.showModal({title:studioWords('flow','time')[props.language==='en'?1:0],content:text(props.booking.plan==='day'?'day_selection_help':'choose_a_start_time_for_a_twohour_a3470d'),showCancel:false});}
watch(()=>[props.booking.date,count.value],()=>{const index=props.calendar.days.findIndex(day=>day.date===props.booking.date);if(index>=0)offset.value=Math.floor(index/count.value)*count.value;},{immediate:true});
watch(()=>props.booking.plan,()=>{choosingEnd.value=false;message.value=false;});
</script>
<template>
 <view class="studio-calendar">
  <view class="studio-calendar-legend"><text><text class="studio-slot-dot"/>{{text('available_to_book_9bb918')}}</text><text><text class="studio-slot-dot studio-slot-dot--selected"/>{{text('your_selection_0fc834')}}</text><text><text class="studio-slot-dot studio-slot-dot--closed"/>{{text('unavailable_fb3489')}}</text><text><text class="studio-slot-dot studio-slot-dot--low"/>{{text('low_seats')}}</text></view>
  <view class="studio-calendar-navigation"><button :hover-stay-time="180" :hover-start-time="0" :disabled="disabled||offset===0" :aria-label="text('previous_dates_314fc5')" hover-class="studio-native-pressed" @tap="page(-1)"><StudioGlyph name="back" :size="18"/></button><view><text>{{shortDate(days[0]?.date||'',language)}} – {{shortDate(days[days.length-1]?.date||'',language)}}</text><text class="studio-native-site">{{studioWords('receipt','hamilton_local_time_496f95')[language==='en'?1:0]}}</text></view><button :hover-stay-time="180" :hover-start-time="0" :disabled="disabled||offset+count>=calendar.days.length" :aria-label="text('next_dates_4c8209')" hover-class="studio-native-pressed" @tap="page(1)"><StudioGlyph name="arrow" :size="18"/></button></view>
  <view class="studio-calendar-head" :style="{'--calendar-days':days.length}"><text>{{text('time_296653')}}</text><text v-for="day in days" :key="day.date">{{shortDate(day.date,language)}}</text></view>
  <scroll-view class="studio-calendar-scroll" scroll-y :show-scrollbar="true">
   <view v-for="row in rows" :key="row.time" class="studio-calendar-row" :style="{'--calendar-days':days.length}"><text class="studio-calendar-time">{{row.time}}</text><button :hover-stay-time="180" :hover-start-time="0" v-for="(day,di) in days" :key="day.date" class="studio-calendar-cell" :class="{'studio-calendar-cell--selected':selected(day.date,row.time),'studio-calendar-cell--closed':!day.slots[row.index]?.available,'studio-calendar-cell--low':day.slots[row.index]?.low_capacity}" :disabled="disabled||!day.slots[row.index]?.available" :aria-label="day.date+' '+row.time+' '+text(day.slots[row.index]?.available?'available_d07da8':'unavailable_e939b7')+' '+capacityLabel(day.slots[row.index])" hover-class="studio-native-pressed" @tap="choose(di,row.index)"><text v-if="selected(day.date,row.time)&&booking.start===row.time">{{text('start_ba3401')}}</text><text v-else-if="selected(day.date,row.time)&&booking.end===day.slots[row.index]?.end">{{text('end_c4265b')}}</text><view v-else-if="day.slots[row.index]?.available" class="studio-calendar-cell-dot"/><text v-else>—</text></button></view>
   <view class="studio-calendar-end"><text>{{end}}</text><text>{{text('end_c4265b')}}</text></view>
  </scroll-view>
  <text v-if="message" class="studio-native-error">{{text('choose_an_earlier_or_another_available_time_f98d07')}}</text>
  <view class="studio-calendar-help"><text class="studio-native-body studio-native-small">{{studioWords('visit','choose_a_time_in_the_timetable_d988a8')[language==='en'?1:0]}}</text><button :hover-stay-time="180" :hover-start-time="0" hover-class="studio-native-pressed" class="studio-native-eye" :aria-label="text(booking.plan==='day'?'day_selection_help':'choose_a_start_time_for_a_twohour_a3470d')" @tap="help"><StudioGlyph name="info" :size="18"/></button></view>
  <text class="studio-native-body studio-native-small">{{studioWords('flow','overtime_notice')[language==='en'?1:0]}}</text>
 </view>
</template>
