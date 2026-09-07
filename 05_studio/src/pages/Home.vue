<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from "vue";
import {
  PhArrowDown,
  PhArrowRight,
  PhArrowUpRight,
  PhFlower,
  PhMapPin,
} from "@phosphor-icons/vue";
import { gsap } from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import PhotoViewer from "../components/PhotoViewer.vue";
import BeadMark from "../components/BeadMark.vue";
import { gallery, mapsUrl, media, socialUrl, tr, wechat } from "../state";
import { catalog, loadCatalog } from "../commerce";

gsap.registerPlugin(ScrollTrigger);
const page = ref<HTMLElement>();
const viewer = ref<InstanceType<typeof PhotoViewer>>();
const copied = ref(false);
const hourlyPrice = computed(
  () => catalog.value?.products.find((p) => p.id === "hourly")?.price_cents,
);
let motion: gsap.MatchMedia | undefined;
let copyTimer: ReturnType<typeof setTimeout> | undefined;
onMounted(() => {
  loadCatalog().catch(() => {
    /* The visit page offers a retry if the catalog is unavailable. */
  });
  motion = gsap.matchMedia();
  motion.add(
    "(prefers-reduced-motion: no-preference)",
    () => {
      gsap.from(".hero-copy > *", {
        y: 22,
        opacity: 0.25,
        stagger: 0.08,
        duration: 0.8,
        ease: "power3.out",
        clearProps: "all",
      });
      gsap.from(".hero-photo", {
        clipPath: "inset(0 0 12% 0)",
        duration: 1.1,
        ease: "power3.out",
        clearProps: "clipPath",
      });
      gsap.fromTo(
        ".space-photo img",
        { yPercent: -3 },
        {
          yPercent: 3,
          ease: "none",
          scrollTrigger: {
            trigger: ".space-photo",
            start: "top bottom",
            end: "bottom top",
            scrub: 1,
          },
        },
      );
    },
    page.value,
  );
});
onBeforeUnmount(() => {
  motion?.revert();
  clearTimeout(copyTimer);
});
async function copyContact() {
  try {
    await navigator.clipboard.writeText(wechat);
    copied.value = true;
    copyTimer = setTimeout(() => (copied.value = false), 2500);
  } catch {
    copied.value = false;
  }
}
</script>

<template>
  <div ref="page">
    <section class="hero container">
      <div class="hero-copy">
        <div class="hero-location">
          <span class="location-dot"></span>HAMILTON, ONTARIO
        </div>
        <h1>
          {{ tr("留一点时间，", "A little time.") }}<br /><em>{{
            tr("给喜欢的小事。", "A little colour.")
          }}</em>
        </h1>
        <p class="hero-description">
          {{
            tr(
              "欢迎来到小狗拼豆铺。选一幅喜欢的图，坐进阳光里，把一颗颗小豆子，变成属于你的快乐。",
              "Welcome to our little bead studio. Pull up a chair, pick a pattern, and turn a handful of tiny beads into something that is entirely yours.",
            )
          }}
        </p>
        <div class="hero-buttons">
          <RouterLink class="button button-primary" to="/visit"
            >{{ tr("来拼豆吧", "Come make something")
            }}<PhArrowUpRight :size="20" /></RouterLink
          ><RouterLink class="text-link" to="/#space"
            >{{ tr("先逛逛小屋", "Take a look around")
            }}<PhArrowDown :size="16"
          /></RouterLink>
        </div>
        <div class="hero-footnote">
          <BeadMark />
          <span>{{
            tr(
              "不用很擅长，只要很喜欢。",
              "No experience. Just a little curiosity.",
            )
          }}</span>
        </div>
      </div>
      <div class="hero-photo">
        <img
          :src="media('studio-02')"
          :alt="
            tr(
              '小狗拼豆铺实景，阳光里的白色工作台与彩色拼豆作品墙',
              'The real PinDou Puppy studio, with white worktables and a colourful bead art wall',
            )
          "
          width="1080"
          height="1440"
          fetchpriority="high"
        />
        <div class="photo-caption">
          <span>OUR LITTLE HAPPY PLACE</span><PhArrowDown :size="17" />
        </div>
        <div class="hero-stamp" aria-hidden="true">
          <PhFlower :size="29" weight="light" /><span
            >made<br /><em>by you.</em></span
          >
        </div>
      </div>
    </section>

    <div class="welcome-strip">
      <span>{{ tr("一个人放空", "A little me-time") }}</span
      ><PhFlower aria-hidden="true" /><span>{{
        tr("和朋友一起", "An afternoon with friends")
      }}</span
      ><PhFlower aria-hidden="true" /><span>{{
        tr("把心意带回家", "Something to take home")
      }}</span
      ><PhFlower aria-hidden="true" /><span>{{
        tr("慢慢来，没关系", "Make yourself at home")
      }}</span>
    </div>

    <section id="space" class="space-section container section-space">
      <div class="space-photo">
        <img
          :src="media('studio-04')"
          width="1080"
          height="1440"
          loading="lazy"
          :alt="
            tr(
              '窗边自然光照进独立的拼豆工作台',
              'Natural light falls across the individual worktables',
            )
          "
        /><span class="small-photo-note">a corner to call your own.</span>
      </div>
      <div class="space-copy">
        <h2>
          {{ tr("小小的房间，", "A small room.") }}<br /><em>{{
            tr("装得下好多喜欢。", "So many possibilities.")
          }}</em>
        </h2>
        <p>
          {{
            tr(
              "我们把家里的一个房间，慢慢变成了拼豆小屋。每个人都有自己的位置，桌上放好豆子和工具，墙上是越拼越满的喜欢。",
              "We turned a room at home into a space for making. A seat of your own, beads and tools within reach, and walls that fill up with the things we love.",
            )
          }}
        </p>
        <p>
          {{
            tr(
              "你可以一个人来，安安静静地拼；也可以约上朋友，边聊天边做。选图、配色、烫豆，都可以一起慢慢来。",
              "Come on your own for a quiet moment, or bring a friend and catch up over a pattern. We are here to help with colours, ideas and the finishing touches.",
            )
          }}
        </p>
        <RouterLink class="text-link" to="/journal"
          >{{ tr("看看小屋的日常", "A little more of the studio")
          }}<PhArrowRight
        /></RouterLink>
        <div class="space-signature">
          see you at puppy.<PhFlower :size="26" weight="light" />
        </div>
      </div>
    </section>

    <section class="work-section section-space">
      <div class="container">
        <div class="section-heading">
          <h2>
            {{ tr("快乐，有很多种形状。", "Happiness takes many shapes.") }}
          </h2>
          <RouterLink class="text-link" to="/journal"
            >{{ tr("翻翻作品日记", "The studio journal") }}<PhArrowUpRight
          /></RouterLink>
        </div>
        <div class="work-grid">
          <button
            v-for="(item, index) in [gallery[1], gallery[2], gallery[4]]"
            :key="item.image"
            class="photo-tile"
            @click="viewer?.open([1, 2, 4][index])"
          >
            <div class="photo-tile-image">
              <img
                :src="media(item.image)"
                :alt="tr(item.zh, item.en)"
                width="1080"
                height="1440"
                loading="lazy"
              /><span class="photo-expand"><PhArrowUpRight /></span>
            </div>
            <span>{{ tr(item.zh, item.en) }}</span>
          </button>
        </div>
        <div class="work-caption">
          <PhFlower :size="20" weight="light" /><span>{{
            tr(
              "挂件、冰箱贴、小小的风景……从喜欢的那一件开始。",
              "Charms, magnets, tiny landscapes. Start with something you love.",
            )
          }}</span>
        </div>
      </div>
    </section>

    <section class="visit-teaser container section-space">
      <div class="visit-teaser-heading">
        <h2>
          {{ tr("这一会儿，", "An afternoon,") }}<br /><em>{{
            tr("只管开心。", "just for you.")
          }}</em>
        </h2>
        <RouterLink class="button button-primary" to="/visit"
          >{{ tr("安排一次到访", "Plan your visit") }}<PhArrowUpRight
        /></RouterLink>
      </div>
      <div class="visit-details">
        <div class="visit-price">
          <span>{{ tr("按时体验", "Pay by the hour") }}</span>
          <div>
            <sup>CA$</sup>{{ hourlyPrice ? hourlyPrice / 100 : "—"
            }}<span>{{ tr("/ 人 / 小时", "/ person / hour") }}</span>
          </div>
        </div>
        <div class="visit-inclusions">
          <p>
            {{
              tr(
                "自己的座位，齐全的工具",
                "Your own seat. All the little tools.",
              )
            }}
          </p>
          <p>
            {{
              tr(
                "选图和配色，一起慢慢来",
                "A little help with patterns and colours.",
              )
            }}
          </p>
          <p>
            {{
              tr(
                "烫好以后，把快乐带走",
                "A finished little piece to take home.",
              )
            }}
          </p>
        </div>
        <p class="fine-print">
          {{
            tr(
              "也有单人和双人全天体验。选好可用时段，付款后即确认座位。",
              "Day passes for one or two are also available. Choose an available time; payment confirms your seats.",
            )
          }}
        </p>
      </div>
    </section>

    <section class="shop-teaser container">
      <div class="shop-teaser-image">
        <img
          :src="media('studio-11')"
          width="1080"
          height="1440"
          loading="lazy"
          :alt="
            tr(
              '分类收纳的彩色挂件与手作配件',
              'Colourful charms and craft fittings, sorted and ready',
            )
          "
        />
      </div>
      <div class="shop-teaser-copy">
        <h2>
          {{ tr("把灵感，", "Take a little") }}<br /><em>{{
            tr("也带回家。", "inspiration home.")
          }}</em>
        </h2>
        <p>
          {{
            tr(
              "想在家继续拼？来小店挑工具、补颜色，选一份喜欢的手作。放进购物车，付款后到店带走。",
              "Keep making at home. Explore tools, top up your colours, or choose a handmade piece. Add your favourites to your bag, pay online and collect at the studio.",
            )
          }}
        </p>
        <RouterLink to="/shop" class="button button-outline"
          >{{ tr("逛逛拼豆小店", "Explore the little shop") }}<PhArrowUpRight
        /></RouterLink>
      </div>
    </section>

    <section id="find-us" class="find-section container section-space">
      <div>
        <h2>
          {{ tr("在 Hamilton，", "A little hello") }}<br /><em>{{
            tr("等你来玩。", "from Hamilton.")
          }}</em>
        </h2>
        <p>
          {{
            tr(
              "提前约好时间，再把这一天留给喜欢的事。",
              "Make a little time, book a visit, and come create with us.",
            )
          }}
        </p>
        <a class="address-link" :href="mapsUrl" target="_blank" rel="noreferrer"
          ><PhMapPin :size="25" weight="light" /><span
            >8 Hughson St N<br />Hamilton, Ontario</span
          ><PhArrowUpRight :size="20"
        /></a>
      </div>
      <div class="find-details">
        <details open>
          <summary>{{ tr("到店前的小提醒", "Before you visit") }}</summary>
          <p>
            {{
              tr(
                "这里是预约制的 Home Studio。请按付款成功后订单中确认的时段到店；楼层和停车安排，请提前联系店主。",
                "We welcome visits by appointment. Arrive at the time confirmed on your paid order, and check arrival and parking details with the host beforehand.",
              )
            }}
          </p>
        </details>
        <details>
          <summary>
            {{
              tr(
                "第一次拼豆，也可以来吗？",
                "Can I come if I have never tried this?",
              )
            }}
          </summary>
          <p>
            {{
              tr(
                "当然。先选喜欢的图，从一颗豆子开始。想做什么、需要什么帮助，都可以在预约时告诉我们。",
                "Absolutely. Pick a pattern you love and start with a single bead. Tell us what you would like to make and any help you need when you request a visit.",
              )
            }}
          </p>
        </details>
        <div class="contact-row">
          <a
            class="text-link"
            :href="socialUrl"
            target="_blank"
            rel="noreferrer"
            >{{ tr("小红书 · 小狗双吉", "Meet us on Xiaohongshu")
            }}<PhArrowUpRight /></a
          ><button class="copy-contact" @click="copyContact">
            {{
              copied
                ? tr("微信号已复制", "WeChat ID copied")
                : `WeChat: ${wechat}`
            }}</button
          ><span class="sr-only" role="status">{{
            copied ? tr("微信号已复制", "WeChat ID copied") : ""
          }}</span>
        </div>
      </div>
    </section>
    <PhotoViewer ref="viewer" :photos="gallery" />
  </div>
</template>
