<script setup lang="ts">
import { contentModule } from "../content-store";
const copyText = contentModule("pages-Home", copyTextDefault);

import copyTextDefault from "../content/pages-Home.json";
import { say } from "../state";

import { onBeforeUnmount, onMounted, ref } from "vue";
import { PhArrowUpRight, PhArrowRight, PhFlower } from "@phosphor-icons/vue";
import { gsap } from "gsap";
import PhotoViewer from "../components/PhotoViewer.vue";
import StudioImage from "../components/StudioImage.vue";
import StudioCarousel from "../components/StudioCarousel.vue";
import BrandMotif from "../components/BrandMotif.vue";
import { gallery, media, tr } from "../state";
import { reducedMotion, onMotionPreferenceChange } from "../motion-preference";
const page = ref<HTMLElement>();
const viewer = ref<InstanceType<typeof PhotoViewer>>();
let animation: gsap.Context | undefined;
let stopPreference: (() => void) | undefined;
function entrance() {
  animation?.revert();
  animation = undefined;
  if (reducedMotion()) return;
  animation = gsap.context(() => {
    gsap
      .timeline({ defaults: { ease: "studio-travel" } })
      .from(
        ".vision-title > span",
        {
          y: 24,
          opacity: 0,
          duration: 1.05,
          stagger: 0.12,
          clearProps: "transform,opacity",
        },
        0,
      )
      .from(
        ".hero-puppy",
        { rotation: -8, y: 10, opacity: 0, duration: 1.2, clearProps: "all" },
        0.3,
      )
      .from(
        ".hero-star, .hero-heart",
        {
          scale: 0.75,
          rotation: 12,
          opacity: 0,
          duration: 1.1,
          stagger: 0.16,
          clearProps: "all",
        },
        0.55,
      )
      .from(
        ".vision-hero-description",
        { y: 12, opacity: 0, duration: 1, clearProps: "transform,opacity" },
        0.22,
      )
      .from(
        ".vision-hero-photo",
        {
          clipPath: "inset(3% 0 5% 0 round 16px)",
          duration: 1.35,
          clearProps: "clipPath",
        },
        0.18,
      );
  }, page.value);
}
onMounted(() => {
  entrance();
  stopPreference = onMotionPreferenceChange(entrance);
});
onBeforeUnmount(() => {
  stopPreference?.();
  animation?.revert();
});
</script>
<template>
  <div ref="page" class="vision-home">
    <section class="vision-hero container">
      <p class="vision-location">
        {{ say(copyText.hamilton_ontario_canada_fbf034) }}
      </p>
      <div class="vision-hero-lettering">
        <BrandMotif class="hero-puppy" /><BrandMotif
          kind="star" interactive
          class="hero-star"
        /><BrandMotif kind="heart" interactive class="hero-heart" />
        <h1 class="vision-title">
          <span>{{ say(copyText.a_little_time_all_yours_9e9d60) }}</span
          ><span>{{ say(copyText.make_something_lovely_04db64) }}</span>
        </h1>
      </div>
      <p class="vision-hero-description vision-mobile-copy">
        {{ say(copyText.welcome_to_pindo_puppychoose_an_afternoon_and_247303) }}
      </p>
      <p class="vision-hero-description vision-desktop-copy">
        {{ say(copyText.welcome_to_pindo_puppychoose_an_afternoon_and_247303) }}
      </p>
      <figure class="vision-hero-photo">
        <StudioImage name="hero-illustration" :alt="say(copyText.sunlit_worktables_and_a_wall_of_bead_46e326)" sizes="(max-width: 760px) 100vw, 1136px" loading="eager" priority="high" />
      </figure>
      <div class="vision-hero-actions">
        <RouterLink class="button button-primary" to="/visit"
          >{{ say(copyText.come_create_2eee81) }}<PhArrowUpRight
        /></RouterLink>
        <RouterLink class="button button-outline" to="/shop"
          >{{ say(copyText.little_shop_c97261) }}<PhArrowUpRight
        /></RouterLink>
      </div>
    </section>
    <div class="vision-welcome">
      <span>{{ say(copyText.time_for_yourself_9e1db5) }}</span
      ><BrandMotif kind="star" /><span>{{
        say(copyText.friends_together_71ba0c)
      }}</span
      ><BrandMotif kind="star" /><span>{{
        say(copyText.made_by_hand_f4654d)
      }}</span>
    </div>
    <section id="space" class="vision-space container">
      <StudioCarousel />
      <div class="vision-space-copy">
        <p class="vision-eyebrow">
          {{ say(copyText.welcome_to_pindo_puppy_2b7fcf) }}
        </p>
        <h2>
          {{ say(copyText.a_little_workshop_32499a) }}<br /><em>{{
            say(copyText.endless_lovely_possibilities_b5a1fa)
          }}</em>
        </h2>
        <p>
          {{ say(copyText.we_turned_a_room_in_our_home_3b9cec) }}
        </p>
        <p>
          {{ say(copyText.come_for_a_beadmaking_experience_pick_up_061846) }}
        </p>
        <p>
          {{ say(copyText.come_alone_for_a_quiet_moment_or_6cec34) }}
        </p>
        <p>
          {{ say(copyText.slow_down_at_pindo_puppy_and_enjoy_8b796a) }}
        </p>
        <RouterLink class="text-link" to="/details"
          >{{ say(copyText.studio_details_7c4089) }}<PhArrowRight
        /></RouterLink>
      </div>
    </section>
    <section class="vision-journal">
      <div class="container">
        <div class="vision-section-heading">
          <h2>
            {{ say(copyText.happiness_takes_many_shapes_c5b449) }}
          </h2>
          <RouterLink class="text-link" to="/journal"
            >{{ say(copyText.browse_the_studio_journal_39842d)
            }}<PhArrowUpRight
          /></RouterLink>
        </div>
        <div class="vision-journal-grid">
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
      </div>
    </section>
    <section class="vision-experience container">
      <div>
        <BrandMotif kind="bone" interactive class="experience-motif" />
        <h2>
          {{ say(copyText.how_about_bf459e) }}<br /><em>{{
            say(copyText.giving_it_a_try_9e9961)
          }}</em>
        </h2>
        <RouterLink class="button button-primary" to="/visit"
          >{{ say(copyText.book_a_beadmaking_visit_ec7a0a) }}<PhArrowUpRight
        /></RouterLink>
      </div>
      <ul>
        <li>
          <span>01</span>{{ say(copyText.a_seat_of_your_own_and_a_f9a329) }}
        </li>
        <li>
          <span>02</span
          >{{ say(copyText.your_group_your_own_set_of_beads_c2a8a9) }}
        </li>
        <li>
          <span>03</span
          >{{ say(copyText.all_the_tools_you_need_choose_a_198a68) }}
        </li>
        <li>
          <span>04</span
          >{{
            say(
              copyText.special_ironing_techniques_for_different_textures_dffbdd,
            )
          }}
        </li>
      </ul>
    </section>
    <section class="vision-shop-teaser container">
      <StudioImage name="shop-collage" :alt="say(copyText.charms_and_craft_fittings_in_the_studio_183b2f)" />
      <div>
        <h2>
          {{ say(copyText.or_take_a_little_38633e) }}<br /><em>{{
            say(copyText.happiness_home_4ed870)
          }}</em>
        </h2>
        <p>
          {{ say(copyText.our_little_shop_is_still_taking_shape_bf9bb8) }}
        </p>
        <RouterLink class="text-link" to="/shop"
          >{{ say(copyText.visit_the_little_shop_b5f393) }}<PhArrowRight
        /></RouterLink>
      </div>
    </section>
    <PhotoViewer ref="viewer" :photos="gallery" />
  </div>
</template>
