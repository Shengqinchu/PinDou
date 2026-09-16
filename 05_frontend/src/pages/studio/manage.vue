<script setup lang="ts">
import StudioWorkspacePane from '../../components/StudioWorkspacePane.vue';
import {useWorkspace} from '../../utils/studio-workspace';
import AdminHome from '../../components/workspace/AdminHome.vue';
import AdminReservations from '../../components/workspace/AdminReservations.vue';
import AdminMessages from '../../components/workspace/AdminMessages.vue';
import AdminFinance from '../../components/workspace/AdminFinance.vue';
const {tab,visible,visited,query,scope,shellStyle}=useWorkspace('admin');
</script>
<template><view class="studio-workspace" :style="shellStyle">
  <StudioWorkspacePane v-if="visited.home" :key="scope+':home'" :active="visible&&tab==='home'" :query="query"><AdminHome/></StudioWorkspacePane>
  <StudioWorkspacePane v-if="visited.reservations" :key="scope+':reservations'" :active="visible&&tab==='reservations'" :query="query"><AdminReservations/></StudioWorkspacePane>
  <StudioWorkspacePane v-if="visited.messages" :key="scope+':messages'" :active="visible&&tab==='messages'" :query="query"><AdminMessages/></StudioWorkspacePane>
  <StudioWorkspacePane v-if="visited.finance" :key="scope+':finance'" :active="visible&&tab==='finance'" :query="query"><AdminFinance/></StudioWorkspacePane>
</view></template>
<style>.studio-workspace{height:var(--studio-window-height,100vh);overflow:hidden;min-height:0}</style>
