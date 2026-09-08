import { createApp } from "vue";
import { createRouter, createWebHistory } from "vue-router";
import "@fontsource/dm-serif-display/latin-400.css";
import "@fontsource/dm-serif-display/latin-400-italic.css";
import "@fontsource-variable/outfit";
import "./style.css";
import "./styles/typography.css";
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
import "./styles/reduced-motion.css";
import { installMotionPreference } from "./motion-preference";
import { installMotion } from "./motion";
import { installViewport } from "./browser";
import { reducedMotion } from "./ui";
import App from "./App.vue";
import Home from "./pages/Home.vue";

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    { path: "/", component: Home },
    { path: "/visit", component: () => import("./pages/Visit.vue") },
    {
      path: "/reservation/:id",
      component: () => import("./pages/ReservationReceipt.vue"),
    },
    { path: "/details", component: () => import("./pages/Details.vue") },
    { path: "/shop", component: () => import("./pages/Shop.vue") },
    { path: "/cart", redirect: "/shop" },
    { path: "/order/:id", component: () => import("./pages/Order.vue") },
    { path: "/journal", component: () => import("./pages/Journal.vue") },
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

const stopPreference = installMotionPreference();
const stopMotion = installMotion();
const stopViewport = installViewport();
createApp(App).use(router).mount("#app");
if (import.meta.hot)
  import.meta.hot.dispose(() => {
    stopMotion();
    stopPreference();
    stopViewport();
  });
