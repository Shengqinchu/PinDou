<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from "vue";
import { PhArrowUpRight, PhArrowRight, PhFlower } from "@phosphor-icons/vue";
import { gsap } from "gsap";
import PhotoViewer from "../components/PhotoViewer.vue";
import StudioCarousel from "../components/StudioCarousel.vue";
import { gallery, media, tr } from "../state";
const page = ref<HTMLElement>();
const viewer = ref<InstanceType<typeof PhotoViewer>>();
let animation: gsap.MatchMedia | undefined;
onMounted(() => {
  animation = gsap.matchMedia();
  animation.add("(prefers-reduced-motion: no-preference)", () => {
    gsap.timeline({ defaults: { ease: "studio-travel" } })
      .from(".vision-title > span", { y: 24, opacity: 0, duration: 1.05, stagger: 0.12, clearProps: "transform,opacity" }, 0)
      .from(".vision-hero-description", { y: 12, opacity: 0, duration: 1, clearProps: "transform,opacity" }, 0.22)
      .from(".vision-hero-photo", { clipPath: "inset(3% 0 5% 0 round 16px)", duration: 1.35, clearProps: "clipPath" }, 0.18);
  }, page.value);
});
onBeforeUnmount(() => animation?.revert());
</script>
<template>
  <div ref="page" class="vision-home">
    <section class="vision-hero container">
      <p class="vision-location">{{ tr("加拿大 · 安大略省 · 汉密尔顿", "Hamilton, Ontario, Canada") }}</p>
      <h1 class="vision-title"><span>{{ tr("属于你的", "A little time. All yours.") }}</span><span>{{ tr("全新拼豆手作体验", "Make something lovely.") }}</span></h1>
      <p class="vision-hero-description vision-mobile-copy">{{ tr("也许是一个下午，几件小物，与自己独处的温馨时间。", "An afternoon, a few little things, and a warm moment to yourself.") }}</p>
      <p class="vision-hero-description vision-desktop-copy">{{ tr("欢迎光临小狗拼豆铺。也许是某个下午吧，选自己喜欢的图，坐进阳光里，把一颗颗豆子，变成独属于你的快乐。", "Welcome to Pindo Puppy. Spend an afternoon in the sunshine, choose a pattern you love, and turn tiny beads into a little happiness of your own.") }}</p>
      <figure class="vision-hero-photo"><img :src="media('studio-02')" :alt="tr('小狗拼豆铺的白色工作台、拼豆作品墙与自然光', 'Sunlit worktables and a wall of bead art at Pindo Puppy')" width="1080" height="1440" fetchpriority="high" /></figure>
      <div class="vision-hero-actions">
        <RouterLink class="button button-primary" to="/visit">{{ tr("来拼豆吧", "Come create") }}<PhArrowUpRight /></RouterLink>
        <RouterLink class="button button-outline" to="/shop">{{ tr("拼豆小店", "Little shop") }}<PhArrowUpRight /></RouterLink>
      </div>
    </section>
    <div class="vision-welcome"><span>{{ tr("一人放空", "Time for yourself") }}</span><PhFlower aria-hidden="true" /><span>{{ tr("朋友一起", "Friends together") }}</span><PhFlower aria-hidden="true" /><span>{{ tr("手工制作", "Made by hand") }}</span></div>
    <section id="space" class="vision-space container">
      <StudioCarousel />
      <div class="vision-space-copy">
        <p class="vision-eyebrow">{{ tr("欢迎来到小狗拼豆铺", "WELCOME TO PINDO PUPPY") }}</p>
        <h2>{{ tr("小小工作坊，", "A little workshop.") }}<br /><em>{{ tr("创造无限可爱手作。", "Endless lovely possibilities.") }}</em></h2>
        <p>{{ tr("这是一个家庭工作坊，我们把家里的一个房间，慢慢变成了拼豆小屋。", "We turned a room in our home into a little workshop for making things with beads.") }}</p>
        <p>{{ tr("你可以来体验拼豆，也可以购置自己的拼豆工具；你可以买下拼豆作品，也可以定制独一无二的图案。", "Come for a bead-making experience, pick up tools for home, choose a handmade piece, or talk to us about a pattern made just for you.") }}</p>
        <p>{{ tr("一个人来，安安静静地拼；或者约上朋友，边聊边做。", "Come alone for a quiet moment, or bring a friend and catch up while you create.") }}</p>
        <p>{{ tr("在小狗拼豆铺慢下来吧，感受手工的快乐。", "Slow down at Pindo Puppy and enjoy the simple pleasure of making by hand.") }}</p>
        <RouterLink class="text-link" to="/details">{{ tr("拼豆铺详细信息", "Studio details") }}<PhArrowRight /></RouterLink>
      </div>
    </section>
    <section class="vision-journal">
      <div class="container">
        <div class="vision-section-heading"><h2>{{ tr("快乐，有很多种形状。", "Happiness takes many shapes.") }}</h2><RouterLink class="text-link" to="/journal">{{ tr("翻翻小狗日记", "Browse the studio journal") }}<PhArrowUpRight /></RouterLink></div>
        <div class="vision-journal-grid">
          <button v-for="(item, index) in [gallery[1], gallery[2], gallery[4]]" :key="item.image" class="photo-tile" @click="viewer?.open([1,2,4][index])">
            <div class="photo-tile-image"><img :src="media(item.image)" :alt="tr(item.zh,item.en)" width="1080" height="1440" loading="lazy" /><span class="photo-expand"><PhArrowUpRight /></span></div>
            <span>{{ tr(item.zh,item.en) }}</span>
          </button>
        </div>
      </div>
    </section>
    <section class="vision-experience container">
      <div><p class="vision-eyebrow">{{ tr("给自己一点手作时间", "MAKE A LITTLE TIME") }}</p><h2>{{ tr("不如", "How about") }}<br /><em>{{ tr("来体验一下", "giving it a try?") }}</em></h2><RouterLink class="button button-primary" to="/visit">{{ tr("预约一次拼豆", "Book a bead-making visit") }}<PhArrowUpRight /></RouterLink></div>
      <ul>
        <li><span>01</span>{{ tr("独立座位，舒适的老板椅", "A seat of your own and a comfortable chair") }}</li>
        <li><span>02</span>{{ tr("一组客人一套拼豆，自由轻松", "Your group, your own set of beads") }}</li>
        <li><span>03</span>{{ tr("工具齐全，选好图纸慢慢拼", "All the tools you need; choose a pattern and take your time") }}</li>
        <li><span>04</span>{{ tr("多种特殊烫，实现不同纹理", "Special ironing techniques for different textures") }}</li>
      </ul>
    </section>
    <section class="vision-shop-teaser container">
      <img :src="media('studio-11')" :alt="tr('工作室的挂件与手作配件', 'Charms and craft fittings in the studio')" width="1080" height="1440" loading="lazy" />
      <div><p class="vision-eyebrow">{{ tr("拼豆小店", "THE LITTLE SHOP") }}</p><h2>{{ tr("或者", "Or take a little") }}<br /><em>{{ tr("直接带回家", "happiness home.") }}</em></h2><p>{{ tr("功能尚在开发中，敬请期待……", "Our little shop is still taking shape. Coming soon…") }}</p><RouterLink class="text-link" to="/shop">{{ tr("看看小店", "Visit the little shop") }}<PhArrowRight /></RouterLink></div>
    </section>
    <PhotoViewer ref="viewer" :photos="gallery" />
  </div>
</template>
