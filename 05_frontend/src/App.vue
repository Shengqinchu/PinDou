<script setup lang="ts">
import {onLaunch} from '@dcloudio/uni-app';
import {useUserStore} from './store/studio-user';
onLaunch(()=>{
 const user=useUserStore();
 // Public studio pages never trigger sign-in or account creation.
 if(user.token)void user.fetchProfile().catch(()=>{});
});
</script>
<style lang="scss">
@import "./static/styles/studio-admin.css";
@import "./static/styles/studio-auth.css";
@import "./static/styles/studio-booking.css";
@import "./static/styles/studio-compact.css";
@import "./static/styles/studio-motion.css";
page{background:#fff;color:#2f3438;font-family:'Studio Outfit',-apple-system,BlinkMacSystemFont,'PingFang SC',sans-serif;font-size:16px;line-height:1.6;box-sizing:border-box}
view,scroll-view,text,image,button,input,textarea{box-sizing:border-box}
/* #ifdef H5 */
*,*::before,*::after{box-sizing:border-box}
html,body,uni-page-body{background:#fff}
uni-page-body:has(.studio-native--fitted){min-height:0}
/* #endif */
</style>
