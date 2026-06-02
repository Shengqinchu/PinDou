<template>
  <div class="app-shell">
    <header class="app-header">
      <RouterLink class="brand" to="/" aria-label="PinDou 首页">
        <span class="brand__mark" aria-hidden="true"></span>
        <span class="brand__text">PinDou 拼豆</span>
      </RouterLink>
      <nav class="app-nav" aria-label="主导航">
        <RouterLink to="/">首页</RouterLink>
        <RouterLink to="/works">作品集</RouterLink>
        <RouterLink to="/me">我的</RouterLink>
      </nav>
    </header>

    <main class="app-main">
      <RouterView />
    </main>
  </div>
</template>

