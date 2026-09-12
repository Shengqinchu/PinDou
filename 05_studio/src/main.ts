import { createApp } from "vue";
import { createPinia } from 'pinia';
import { generatorRoutes } from '../../05_generator/src/routes';
import { createRouter, createWebHistory } from "vue-router";
import "@fontsource/dm-serif-display/latin-400.css";
import "@fontsource/dm-serif-display/latin-400-italic.css";
import "@fontsource-variable/outfit";
import "./style.css";
import "./styles/typography.css";
import "./styles/handwriting-fonts.css";
import "./styles/interactions.css";
import "./styles/layout.css";
import "./styles/commerce.css";
import "./styles/overlays.css";
import "./styles/motion.css";
import "./styles/viewport.css";
import "./styles/vision.css";
import "./styles/reservations.css";
import "./styles/journal.css";
import "./styles/desk.css";
import "./styles/tactile.css";
import "./styles/vision3.css";
import "./styles/editor.css";
import "./styles/account.css";
import "./styles/process.css";
import "./styles/copy-contact.css";
import "./styles/responsive.css";
import "./styles/arrival-photos.css";
import "./styles/wallet.css";
import "./styles/home-journal.css";
import "./styles/reduced-motion.css";
import "./styles/timetable.css";
import "./styles/cancellation.css";
import "./styles/generator-motion.css";
import { installContent } from "./content-store";
import { installDiagnostics } from "./diagnostics";
import { installRoutePrefetch, routeLoaders } from "./route-loaders";
import { installMotionPreference } from "./motion-preference";
import { installMotion } from "./motion";
import { installViewport } from "./browser";
import { reducedMotion } from "./ui";
import App from "./App.vue";
import Home from "./pages/Home.vue";
import { preparePreviewRoute } from './preview-context';
preparePreviewRoute();

// A fresh visit starts at the top. Vue Router still restores its saved position
// on back/forward; obsolete shared homepage anchors no longer jump mid-page.
if('scrollRestoration' in history)history.scrollRestoration='manual';
if(/^\/(?:studio\/?)?$/.test(location.pathname)&&location.hash==='#space')
  history.replaceState(history.state,'',location.pathname+location.search);
const router = createRouter({
  history: createWebHistory("/"),
  routes: [
    { path: "/studio/:pathMatch(.*)*", redirect: to => ({path: to.path.replace(/^\/studio/, "") || "/", query: to.query, hash: to.hash}) },
    { path: "/", component: Home },
    { path: "/visit", component: routeLoaders.visit },
    { path: "/account", component: () => import('./pages/Account.vue') },
    { path: '/messages', component: () => import('./pages/Messages.vue') },
    { path: "/auth/wechat", component: () => import('./pages/WechatReturn.vue') },
    { path:'/tools',component:()=>import('../../05_generator/src/Workspace.vue'),children:generatorRoutes },
    ...['upload','loading','result/:id','editor/:id','works','tutorial','me'].map(path=>({path:'/'+path,redirect:(to:any)=>({path:'/tools'+(path==='upload'?'':path==='me'?'/works':to.path),query:to.query,hash:to.hash})})),
    {
      path: "/reservation/:id",
      component: () => import("./pages/ReservationReceipt.vue"),
    },
    { path: "/details", component: routeLoaders.details },
    { path: "/shop", component: routeLoaders.shop },
    { path: "/cart", redirect: "/shop" },
    { path: "/order/:id", component: () => import("./pages/Order.vue") },
    { path: "/journal", component: routeLoaders.journal },
    {
      path: "/journal/:id",
      component: () => import("./pages/JournalEntry.vue"),
    },
    { path: "/manage", component: () => import("./pages/Manage.vue") },
    {
      path: "/:pathMatch(.*)*",
      component: () => import("./pages/NotFound.vue"),
    },
  ],
  scrollBehavior(to, from, saved) {
    if(!from.matched.length)return {top:0,left:0};
    if(to.path==='/visit'&&from.path==='/visit')return false;
    if (saved) return saved;
    if (to.path === from.path && to.query.view !== from.query.view)
      return false;
    if (to.hash)
      return {
        el: to.hash,
        top: 100,
        behavior: reducedMotion() ? "auto" : "smooth",
      };
    return { top: 0 };
  },
});

const stopContent = installContent();
const stopDiagnostics = installDiagnostics();
const stopPrefetch = installRoutePrefetch();
router.afterEach(to => {
  const canonical=document.querySelector<HTMLLinkElement>('link[rel="canonical"]');
  if(canonical)canonical.href="https://pindoupuppy.com"+to.path;
  let robots=document.querySelector<HTMLMetaElement>('meta[name="robots"]');
  if(!robots){robots=document.createElement("meta");robots.name="robots";document.head.appendChild(robots);}
  robots.content=/^\/(manage|reservation|order|account|auth)(\/|$)|^\/tools\/(works|loading|result|editor)(\/|$)/.test(to.path)?"noindex, nofollow":"index, follow";
});
const stopPreference = installMotionPreference();
const stopMotion = installMotion();
const stopViewport = installViewport();
createApp(App).use(createPinia()).use(router).mount("#app");
if (import.meta.hot)
  import.meta.hot.dispose(() => {
    stopContent();
    stopDiagnostics();
    stopPrefetch();
    stopMotion();
    stopPreference();
    stopViewport();
  });
