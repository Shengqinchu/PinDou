<script setup lang="ts">
import {computed,onMounted} from 'vue';
import {accountUser,ensureCustomer} from '../account';
import {customerToken} from '../account-storage';
import {say} from '../state';
import copy from '../content/customer-notifications.json';
import SiteConversation from '../components/SiteConversation.vue';
const ready=computed(()=>!!accountUser.value);
async function login(){try{await ensureCustomer();}catch{}}
onMounted(()=>{if(!customerToken())void login();});
</script>
<template><main class="customer-messages-page"><h1>{{say(copy.messages)}}</h1><SiteConversation v-if="ready" read-only/><button v-else class="button button-primary" @click="login">{{say(copy.sign_in)}}</button></main></template>
<style scoped>.customer-messages-page{width:min(820px,calc(100% - 32px));margin:36px auto 60px}.customer-messages-page h1{font-size:30px;margin-bottom:20px}</style>
