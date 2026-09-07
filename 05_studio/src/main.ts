import { createApp } from "vue";
import { createRouter, createWebHistory } from "vue-router";
import "@fontsource/dm-serif-display/latin-400.css";
import "@fontsource/dm-serif-display/latin-400-italic.css";
import "@fontsource-variable/outfit";
import "./style.css";
import App from "./App.vue";
import Home from "./pages/Home.vue";

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    { path: "/", component: Home },
    { path: "/visit", component: () => import("./pages/Visit.vue") },
    { path: "/shop", component: () => import("./pages/Shop.vue") },
    { path: "/journal", component: () => import("./pages/Journal.vue") },
    { path: "/manage", component: () => import("./pages/Manage.vue") },
    {
      path: "/:pathMatch(.*)*",
      component: () => import("./pages/NotFound.vue"),
    },
  ],
  scrollBehavior(to, _from, saved) {
    if (saved) return saved;
    if (to.hash) return { el: to.hash, top: 100, behavior: "smooth" };
    return { top: 0 };
  },
});

createApp(App).use(router).mount("#app");
