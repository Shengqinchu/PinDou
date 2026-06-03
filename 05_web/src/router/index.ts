import type { Router } from 'vue-router';
import { createRouter, createWebHistory } from 'vue-router';

import { clearStoredUser, clearToken, hasToken } from '../auth/tokenStorage';
import HomePage from '../views/HomePage.vue';
import LoginPage from '../views/LoginPage.vue';
import LoadingPage from '../views/LoadingPage.vue';
import MePage from '../views/MePage.vue';
import PlaceholderPage from '../views/PlaceholderPage.vue';
import ResultPage from '../views/ResultPage.vue';
import UploadPage from '../views/UploadPage.vue';

const protectedRoutes = new Set(['upload', 'loading', 'result', 'works', 'me']);

export const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', name: 'home', component: HomePage },
    { path: '/login', name: 'login', component: LoginPage },
    {
      path: '/upload',
      name: 'upload',
      component: UploadPage,
      meta: { title: '上传', requiresAuth: true }
    },
    {
      path: '/loading',
      name: 'loading',
      component: LoadingPage,
      meta: { title: '生成中', requiresAuth: true }
    },
    {
      path: '/result/:id',
      name: 'result',
      component: ResultPage,
      meta: { title: '结果', requiresAuth: true }
    },
    {
      path: '/works',
      name: 'works',
      component: PlaceholderPage,
      meta: { title: '作品集', requiresAuth: true }
    },
    {
      path: '/me',
      name: 'me',
      component: MePage,
      meta: { title: '我的', requiresAuth: true }
    },
    { path: '/:pathMatch(.*)*', redirect: '/' }
  ]
});

router.beforeEach((to) => {
  if (to.meta.requiresAuth || protectedRoutes.has(String(to.name))) {
    if (!hasToken()) {
      return {
        path: '/login',
        query: { redirect: to.fullPath }
      };
    }
  }
  return true;
});

export function setupAuthRedirect(activeRouter: Router): void {
  window.addEventListener('pindou:auth-expired', () => {
    const current = activeRouter.currentRoute.value;
    if (current.name !== 'login') {
      activeRouter.replace({
        path: '/login',
        query: { redirect: current.fullPath }
      });
    }
  });
}

export function expireAuthSession(): void {
  clearToken();
  clearStoredUser();
  window.dispatchEvent(new CustomEvent('pindou:auth-expired'));
}
