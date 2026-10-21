<script setup lang="ts">
import LiftTitle from '../components/LiftTitle.vue';
import { asset, contentModule, contentPhotos } from "../content-store";
import carouselPhotos from "../content/data-components-StudioCarousel-photos.json";
const copyText = contentModule("pages-Details", copyTextDefault);

import BeadingProcess from "../components/BeadingProcess.vue";
import processDefaults from "../content/components-BeadingProcess.json";
const processCopy=contentModule('components-BeadingProcess',processDefaults);
import { computed, ref } from "vue";
import StudioImage from "../components/StudioImage.vue";
import PhotoViewer from "../components/PhotoViewer.vue";
import { contacts } from "../state";
import copyTextDefault from "../content/pages-Details.json";
import { say } from "../state";

import {
  PhArrowUpRight,
  PhMapPin,
  PhCar,
  PhBus,
  PhClock,
  PhHandWaving,
} from "@phosphor-icons/vue";
import { media, socialUrl, tr, wechat } from "../state";
const map = (address: string) =>
  "https://www.google.com/maps/search/?api=1&query=" +
  encodeURIComponent(address);
const address = computed(() => say(contacts.address));
const parking = computed(() => [say(contacts.parking_1),say(contacts.parking_2)]);
const visitViewer = ref<InstanceType<typeof PhotoViewer>>();
const visitPhotos = computed(() => [
  { image: 'arrival-entrance', words: copyText.lightfilled_worktables_by_the_studio_window_148082 },
  { image: 'parking-entrance', words: copyText.visitor_parking_entrance_30c573 },
  { image: 'parking-location', words: copyText.visitor_parking_location_c046e2 },
].map(photo => ({ image: photo.image, src: asset(photo.image).src, zh: photo.words[0], en: photo.words[1] })));
// The studio environment gallery shares the home carousel's photographs and captions,
// minus the sunset, the angled mirror and the two display grids (owner, 2026-10-21).
const spaceHidden = new Set(["space-v5-01", "space-v5-09", "space-v5-14", "space-v5-15"]);
const spaceViewer = ref<InstanceType<typeof PhotoViewer>>();
const spacePhotos = contentPhotos("carousel-labels", carouselPhotos);
const spaceItems = computed(() => spacePhotos.filter(photo => !spaceHidden.has(photo.image)).map(photo => ({ image: photo.image, src: asset(photo.image).src, zh: photo.zh, en: photo.en })));
</script>
<template>
  <div class="vision-details container">
    <header class="vision-detail-heading">
      <p class="vision-eyebrow">
        {{ say(copyText.a_little_knowhow_before_you_visit_b1dd61) }}
      </p>
      <LiftTitle :text="say(copyText.a_little_guide_to_the_studio_1b38da)"/>
      <p>
        {{ say(copyText.getting_here_finding_parking_and_the_little_0ec5c9) }}
      </p>
    </header>
    <nav
      class="vision-detail-nav"
      :aria-label="say(copyText.studio_information_sections_45baee)"
    >
      <a href="#arrival">{{ say(copyText.getting_here_1f608d) }}</a
      ><a href="#parking">{{ say(copyText.parking_8188de) }}</a
      ><a href="#space">{{ say(copyText.studio_environment_6f2a91) }}</a
      ><a href="#services">{{ say(copyText.at_the_studio_0bc0c9) }}</a
      ><a href="#notes">{{ say(copyText.good_to_know_fc4515) }}</a>
      <a href="#process">{{ say(processCopy.title) }}</a>
    </nav>
    <section id="arrival" class="vision-arrival">
      <div>
        <PhMapPin :size="30" weight="light" />
        <LiftTitle as="h2" :text="say(copyText.studio_address_171634)"/>
        <a
          class="vision-address"
          :href="map(address)"
          target="_blank"
          rel="noreferrer"
          >{{ address }}<PhArrowUpRight :size="22"
        /></a>
        <p>
          <PhBus :size="20" />{{
            say(copyText.in_downtown_hamilton_accessible_by_local_buses_657f96)
          }}
        </p>
        <p>
          <PhClock :size="20" />{{
            say(copyText.visits_are_by_appointment_you_are_welcome_008328)
          }}
        </p>
        <p>
          <PhHandWaving :size="20" />{{
            say(copyText.the_host_will_meet_you_downstairs_when_aeec4f)
          }}
        </p>
      </div>
      <button class="visit-photo arrival-photo" :aria-label="say(processCopy.photoLabel)+' · '+say(copyText.lightfilled_worktables_by_the_studio_window_148082)" @click="visitViewer?.open(0)">
        <StudioImage name="arrival-entrance" :alt="say(copyText.lightfilled_worktables_by_the_studio_window_148082)" sizes="(max-width:760px) 90vw, 300px" loading="eager" />
      </button>
    </section>
    <section id="parking" class="vision-detail-section">
      <LiftTitle as="h2" :text="say(copyText.a_place_to_park_fcb8e3)"/>
      <p>
        {{
          say(
            copyText.free_visitor_parking_is_available_downstairs_usually_7daf39,
          )
        }}
      </p>
      <div class="vision-parking-photos photos-ready">
        <figure
          v-for="(photo, index) in visitPhotos.slice(1)"
          :key="photo.image"
        >
          <button class="visit-photo parking-photo" :aria-label="say(processCopy.photoLabel)+' · '+say([photo.zh,photo.en])" @click="visitViewer?.open(index+1)">
            <StudioImage :name="photo.image" :alt="say([photo.zh,photo.en])" sizes="(max-width:600px) 90vw, 400px" />
          </button>
          <figcaption>{{ say([photo.zh,photo.en]) }}</figcaption>
        </figure>
      </div>
      <h3>{{ say(copyText.nearby_parking_options_1a311a) }}</h3>
      <div class="vision-parking-links">
        <a
          v-for="place in parking"
          :key="place"
          :href="map(place)"
          target="_blank"
          rel="noreferrer"
          ><PhMapPin :size="20" /><span>{{ place }}</span
          ><PhArrowUpRight :size="18"
        /></a>
      </div>
    </section>
    <PhotoViewer ref="visitViewer" :photos="visitPhotos" />
    <section id="space" class="vision-detail-section studio-space">
      <LiftTitle as="h2" :text="say(copyText.studio_environment_6f2a91)"/>
      <ul class="studio-space-grid">
        <li v-for="(photo, index) in spaceItems" :key="photo.image">
          <button class="studio-space-photo" :aria-label="say(processCopy.photoLabel)+' · '+say([photo.zh,photo.en])" @click="spaceViewer?.open(index)">
            <StudioImage :name="photo.image" :alt="say([photo.zh,photo.en])" sizes="(max-width:760px) 46vw, 260px" />
            <span class="studio-space-caption">{{ say([photo.zh,photo.en]) }}</span>
          </button>
        </li>
      </ul>
      <PhotoViewer ref="spaceViewer" :photos="spaceItems" />
    </section>
    <section id="services" class="vision-detail-section">
      <LiftTitle as="h2" :text="say(copyText.made_comfortable_made_yours_0c8904)"/>
      <div class="vision-service-grid">
        <article>
          <span>01</span>
          <h3>{{ say(copyText.seats_and_tools_4b0a0a) }}</h3>
          <p>
            {{
              say(copyText.a_comfortable_chair_an_individual_seat_and_f15251)
            }}
          </p>
        </article>
        <article>
          <span>02</span>
          <h3>
            {{ say(copyText.textures_and_finishing_touches_6d3e7b) }}
          </h3>
          <p>
            {{
              say(
                copyText.we_keep_exploring_different_ironing_techniques_small_659fdb,
              )
            }}
          </p>
        </article>
        <article>
          <span>03</span>
          <h3>{{ say(copyText.little_things_to_take_with_you_a9cf30) }}</h3>
          <p>
            {{
              say(copyText.standard_magnets_phone_straps_and_charms_are_c11f4d)
            }}
          </p>
        </article>
        <article>
          <span>04</span>
          <h3>{{ say(copyText.take_your_time_512353) }}</h3>
          <p>
            {{
              say(copyText.snacks_fruit_and_drinking_water_are_available_746405)
            }}
          </p>
        </article>
      </div>
    </section>
    <section id="notes" class="vision-detail-section vision-notes">
      <LiftTitle as="h2" :text="say(copyText.a_few_little_notes_7bbea4)"/>
      <details open>
        <summary>
          {{ say(copyText.beads_and_handmade_finishes_cdb69f) }}
        </summary>
        <p>
          {{ say(copyText.some_beads_may_have_mixed_colours_burrs_ac08b3) }}
        </p>
      </details>
      <details open>
        <summary>
          {{ say(copyText.keeping_the_worktable_lovely_4b7731) }}
        </summary>
        <p>
          {{
            say(
              copyText.place_beads_individually_rather_than_scattering_them_2535e2,
            )
          }}
        </p>
      </details>
      <details open>
        <summary>
          {{ say(copyText.time_and_payment_a87618) }}
        </summary>
        <p>
          {{ say(copyText.time_is_measured_by_actual_making_time_8a7c82) }}
        </p>
      </details>
    </section>
    <BeadingProcess />
  </div>
</template>
