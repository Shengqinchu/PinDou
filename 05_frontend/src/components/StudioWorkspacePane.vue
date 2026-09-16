<script setup lang="ts">
import {provideView} from '../utils/studio-view-lifecycle';
defineOptions({options:{styleIsolation:'shared',virtualHost:true}});
const props=defineProps<{active:boolean;query:Record<string,string>}>();
provideView(()=>props.active,()=>props.query);
</script>
<template><view v-show="active" class="studio-workspace-pane"><slot/></view></template>
<style>.studio-workspace-pane{height:100%;min-height:0;overflow:hidden}</style>
