<script setup lang="ts">
import StudioShell from '../../components/StudioShell.vue';
import StudioNotificationChoices from '../../components/StudioNotificationChoices.vue';
import {useStudioNative} from '../../utils/studio-native';
import {useUserStore} from '../../store/user';
import {onShow} from '@dcloudio/uni-app';
const {language,keyboardOpen,shellStyle,changeLanguage}=useStudioNative(),user=useUserStore();
onShow(()=>{if(!user.token)uni.navigateTo({url:'/pages/auth/studio-login'});});
</script>
<template><StudioShell fitted nav="account" :language="language" :keyboard-open="keyboardOpen" :shell-style="shellStyle" @language="changeLanguage"><view class="studio-native-main"><StudioNotificationChoices v-if="user.token" :language="language"/></view></StudioShell></template>
