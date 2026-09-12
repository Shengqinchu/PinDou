<script setup lang="ts">
import {computed,onMounted} from 'vue';
import {useRoute} from 'vue-router';
import {accountUser,ensureCustomer} from '../account';
import {customerToken} from '../account-storage';
import {say} from '../state';
import copy from '../content/customer-notifications.json';
import SiteConversation from '../components/SiteConversation.vue';
const ready=computed(()=>!!accountUser.value),route=useRoute();
async function login(){try{await ensureCustomer();}catch{}}
onMounted(()=>{if(!customerToken())void login();});
</script>
<template><main class="customer-messages-page"><h1>{{say(copy.contact_host)}}</h1><SiteConversation v-if="ready" :reservation-id="typeof route.query.reservation==='string'?route.query.reservation:''"/><button v-else class="button button-primary" @click="login">{{say(copy.sign_in)}}</button></main></template>
<style scoped>.customer-messages-page{width:min(820px,calc(100% - 32px));margin:36px auto 60px}.customer-messages-page h1{font-size:30px;margin-bottom:20px}</style>
