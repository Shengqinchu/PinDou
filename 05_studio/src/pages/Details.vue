<script setup lang="ts">
import { PhArrowUpRight, PhMapPin, PhCar, PhBus, PhFlower } from "@phosphor-icons/vue";
import { media, socialUrl, tr, wechat } from "../state";
const map = (address: string) => "https://www.google.com/maps/search/?api=1&query=" + encodeURIComponent(address);
const address = "8 Hughson St N, Hamilton, ON L8R 0B1";
const parking = ["75 John St N, Hamilton, ON L8R 1H7", "115 King William St, Hamilton, ON L8R 1H8"];
</script>
<template>
  <div class="vision-details container">
    <header class="vision-detail-heading"><p class="vision-eyebrow">{{ tr("到访之前，先认识一下小屋", "A LITTLE KNOW-HOW BEFORE YOU VISIT") }}</p><h1>{{ tr("拼豆铺详细信息", "A little guide to the studio") }}</h1><p>{{ tr("怎么来、在哪里停车，以及来拼豆时我们为你准备的小事。", "Getting here, finding parking, and the little things we have ready for you.") }}</p></header>
    <nav class="vision-detail-nav" :aria-label="tr('店铺信息目录', 'Studio information sections')"><a href="#arrival">{{ tr("地址与交通", "Getting here") }}</a><a href="#parking">{{ tr("停车指引", "Parking") }}</a><a href="#services">{{ tr("拼豆铺服务", "At the studio") }}</a><a href="#notes">{{ tr("温馨提示", "Good to know") }}</a></nav>
    <section id="arrival" class="vision-arrival">
      <div><PhMapPin :size="30" weight="light" /><h2>{{ tr("在市中心，等你来。", "Find us downtown.") }}</h2><a class="vision-address" :href="map(address)" target="_blank" rel="noreferrer">{{ address }}<PhArrowUpRight :size="22" /></a><p><PhBus :size="20" />{{ tr("位于汉密尔顿市中心，公交与城际公共交通可达。", "In downtown Hamilton, accessible by local buses and GO Transit.") }}</p><p>{{ tr("预约到访，可比约定时间稍早一点到。", "Visits are by appointment. You are welcome to arrive a little before your confirmed time.") }}</p></div>
      <img :src="media('studio-04')" :alt="tr('窗边明亮的拼豆工作台', 'Light-filled worktables by the studio window')" width="1080" height="1440" />
    </section>
    <section id="parking" class="vision-detail-section">
      <p class="vision-eyebrow">{{ tr("来时路上的小安排", "ON YOUR WAY HERE") }}</p><h2>{{ tr("停车指引", "A place to park") }}</h2>
      <p>{{ tr("楼下有免费的访客停车位，一般工作日有空位，实际以到访时情况为准。", "Free visitor parking is available downstairs, usually with space on weekdays. Availability can vary when you arrive.") }}</p>
      <div class="vision-parking-photos">
        <figure v-for="(label, index) in [tr('访客停车入口', 'Visitor parking entrance'), tr('访客停车位置', 'Visitor parking location')]" :key="index"><PhCar :size="35" weight="light" /><figcaption>{{ label }}<small>{{ tr("指引照片即将补充", "Photograph to follow") }}</small></figcaption></figure>
      </div>
      <h3>{{ tr("附近也可以停车", "Nearby parking options") }}</h3>
      <div class="vision-parking-links"><a v-for="place in parking" :key="place" :href="map(place)" target="_blank" rel="noreferrer"><PhMapPin :size="20" /><span>{{ place }}</span><PhArrowUpRight :size="18" /></a></div>
    </section>
    <section id="services" class="vision-detail-section">
      <p class="vision-eyebrow">{{ tr("带上喜欢的图，其他慢慢来", "BRING A PATTERN YOU LOVE") }}</p><h2>{{ tr("拼豆铺服务", "Made comfortable, made yours") }}</h2>
      <div class="vision-service-grid">
        <article><span>01</span><h3>{{ tr("自己的座位与工具", "Your own place to create") }}</h3><p>{{ tr("舒适的老板椅、独立座位，一组客人一套拼豆，无需拼桌或共用豆子。桌上配齐工具，操作台的备用工具也可自行取用；缺豆时告诉店主即可。", "A comfortable chair, an individual seat and a set of beads for your group. Tools are ready on the table, with spares at the workbench. Ask the host whenever you need more beads.") }}</p></article>
        <article><span>02</span><h3>{{ tr("特殊烫与不同纹理", "Textures and finishing touches") }}</h3><p>{{ tr("店主持续研究不同烫法。中小图熨烫、小图特殊烫免费；超过 78 格的大图需额外收费。想要的风格，可以先一起聊聊。", "We keep exploring different ironing techniques. Small and medium pieces, including special finishes for small pieces, are ironed free. Larger pieces over 78 grid spaces carry an extra charge, discussed beforehand.") }}</p></article>
        <article><span>03</span><h3>{{ tr("把作品变成小物", "Little things to take with you") }}</h3><p>{{ tr("常规冰箱贴、手机链和挂件制作免费，风铃等复杂款式另计费用。店里也有相框、毛毡板等可现场选购。额外收费都会事先说明，征得你的同意后再做。", "Standard magnets, phone straps and charms are finished free. Complex pieces such as wind chimes cost extra. Frames and felt boards are also available in the studio. We explain any extra charge and ask you before proceeding.") }}</p></article>
        <article><span>04</span><h3>{{ tr("自在待一会儿", "Settle in for a while") }}</h3><p>{{ tr("店里备有零食、水果和饮用水。当天没拼完的图案，可以在店内存放，最长保留 5 天。", "Snacks, fruit and drinking water are available. If you do not finish your pattern that day, we can keep it in the studio for up to five days.") }}</p></article>
      </div>
    </section>
    <section id="notes" class="vision-detail-section vision-notes">
      <PhFlower :size="32" weight="light" /><h2>{{ tr("温馨提示", "A few little notes") }}</h2>
      <details open><summary>{{ tr("关于豆子和手作纹理", "Beads and handmade finishes") }}</summary><p>{{ tr("个别豆子可能有混色、毛刺或静电等出厂情况，通常不影响熨烫。手作熨烫可能留下少量纤维或纹理痕迹；很在意细节的话，可以自行烫豆，店里提供工具。", "Occasional mixed colours, burrs or static are normal material variations and usually do not affect ironing. Handmade finishes may have small fibres or texture marks. If you prefer to iron your own piece, tools are available.") }}</p></details>
      <details open><summary>{{ tr("让工作台保持整齐", "Keeping the worktable lovely") }}</summary><p>{{ tr("请采用正常逐颗拼豆的方式，不使用撒豆等非常规操作。撒落或混合的豆子需自行整理，或另付清洁费用；如需收费，会先和你确认。", "Please place beads individually rather than scattering them. Spilled or mixed beads need to be sorted, or a cleaning fee may apply. Any fee is discussed with you first.") }}</p></details>
      <details><summary>{{ tr("实际时长与分享优惠", "Time and sharing perks") }}</summary><p>{{ tr("计时以实际拼豆时长为准，超出 15 分钟按半小时计。介绍新朋友消费、分享体验（例如小红书）有九折或小礼物等安排，具体适用方式请与店主确认。", "Hourly visits are measured by actual making time; more than 15 minutes counts as half an hour. Referring a new friend or sharing your experience can qualify for a 10% discount or a small gift. Ask the host which offer applies.") }}</p></details>
      <div class="vision-detail-contact"><a class="text-link" :href="socialUrl" target="_blank" rel="noreferrer">{{ tr("小红书 · 小狗双吉", "Find our journal on Xiaohongshu") }}<PhArrowUpRight /></a><p>{{ tr("微信号：", "WeChat: ") }}<span class="contact-id">{{ wechat }}</span></p></div>
    </section>
  </div>
</template>
