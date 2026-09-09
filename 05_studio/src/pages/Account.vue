<script setup lang="ts">
import LiftTitle from '../components/LiftTitle.vue';
import AccountPanel from '../components/AccountPanel.vue';
import { accountCopy as copy } from '../account';
import { accountReturn } from '../wechat';
import { say } from '../state';
import { useRoute } from 'vue-router';
import { onMounted } from 'vue';
import { refreshAccount } from '../account';
const route=useRoute();
function signedIn(){if(route.query.intent==='login')location.assign(accountReturn(route.query.return_to,'/upload'));}
onMounted(async()=>{if(route.query.intent==='login'&&await refreshAccount().catch(()=>false))signedIn();});
</script>
<template><section class="container account-page"><LiftTitle :text="say(copy.account_center)"/><AccountPanel embedded @signed-in="signedIn" /></section></template>
