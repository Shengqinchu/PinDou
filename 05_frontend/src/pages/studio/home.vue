<script setup lang="ts">
import {computed} from 'vue';
import StudioShell from '../../components/StudioShell.vue';
import StudioWorkspacePane from '../../components/StudioWorkspacePane.vue';
import {useWorkspace} from '../../utils/studio-workspace';
import CustomerHome from '../../components/workspace/CustomerHome.vue';
import CustomerBookings from '../../components/workspace/CustomerBookings.vue';
import CustomerAccount from '../../components/workspace/CustomerAccount.vue';
const {tab,visible,visited,query,scope,shellStyle,language,keyboardOpen,changeLanguage}=useWorkspace('customer');
const activeTab=computed(()=>tab.value as 'home'|'bookings'|'account');
</script>
<template><StudioShell id="studio-workspace-shell" fitted workspace :language="language" :keyboard-open="keyboardOpen" :shell-style="shellStyle" :nav="activeTab" @language="changeLanguage">
  <StudioWorkspacePane v-if="visited.home" :key="scope+':home'" :active="visible&&tab==='home'" :query="query"><CustomerHome/></StudioWorkspacePane>
  <StudioWorkspacePane v-if="visited.bookings" :key="scope+':bookings'" :active="visible&&tab==='bookings'" :query="query"><CustomerBookings/></StudioWorkspacePane>
  <StudioWorkspacePane v-if="visited.account" :key="scope+':account'" :active="visible&&tab==='account'" :query="query"><CustomerAccount/></StudioWorkspacePane>
</StudioShell></template>
