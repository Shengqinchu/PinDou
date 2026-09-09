import { createPinia } from 'pinia';
import { createApp } from 'vue';

import App from './App.vue';
import { router, setupAuthRedirect } from './router';
import './styles/tokens.css';
import './styles/app.css';
import { installSharedSession } from './auth/sharedSession';

const app = createApp(App);

app.use(createPinia());
// Both applications use the Studio account entry and the same browser token.
router.beforeEach((to,from)=>{
  if(to.path==='/login'){
    const raw=typeof to.query.redirect==='string'?to.query.redirect:from.fullPath||'/upload';
    const target=/^\/(upload|tutorial|works|loading|(?:editor|result)\/[\w-]+)(?:[?#].*)?$/.test(raw)&&!/[\\\x00-\x1f]/.test(raw)?raw:'/upload';
    location.assign('/account?intent=login&return_to='+encodeURIComponent(target));
    return false;
  }
  return true;
});
app.use(router);
setupAuthRedirect(router);

app.mount('#app');
installSharedSession();
