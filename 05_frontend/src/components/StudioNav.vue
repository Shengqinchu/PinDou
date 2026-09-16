<script setup lang="ts">
import StudioGlyph from './StudioGlyph.vue';
import {studioWords} from '../utils/studio-content';
import {navigateStudio} from '../utils/studio-navigation';
defineOptions({options:{styleIsolation:'shared',virtualHost:true}});
const props=defineProps<{active:'home'|'bookings'|'account';language:string}>();
const items=[{id:'home',path:'/pages/studio/home',icon:'home',module:'app',key:'home_76c92b'},{id:'bookings',path:'/pages/studio/reservations',icon:'calendar',module:'account',key:'my_reservations'},{id:'account',path:'/pages/auth/studio-account',icon:'user',module:'account',key:'account'}] as const;
function go(item:typeof items[number]){
 navigateStudio(item.path);
}
</script>
<template><view class="studio-app-nav" role="navigation"><button :hover-stay-time="180" :hover-start-time="0" v-for="item in items" :key="item.id" :class="{'studio-app-nav-active':active===item.id}" :aria-current="active===item.id?'page':undefined" hover-class="studio-native-pressed" @tap="go(item)"><StudioGlyph :name="item.icon" :size="20"/><text>{{studioWords(item.module,item.key)[language==='en'?1:0]}}</text></button></view></template>
