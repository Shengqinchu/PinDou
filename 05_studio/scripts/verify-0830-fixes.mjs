import { chromium, expect } from "@playwright/test";
import assert from "node:assert/strict";
import { mkdir, writeFile } from "node:fs/promises";
const base = "http://127.0.0.1:5184/studio/";
const out = "../artifacts/studio-0830-fixes";
await mkdir(out, { recursive: true });
const browser = await chromium.launch({ headless: true });
const results = [];
const errors = [];
function captureErrors(page) {
  page.on("pageerror", (e) => errors.push(e.message));
}
try {
  // F01: complete recovery, consecutive failure and preservation of choices.
  const p = await browser.newPage();
  captureErrors(p);
  let catalogs = 0,
    failCatalog = true;
  await p.route("**/studio-api/catalog", (r) => {
    catalogs++;
    return failCatalog
      ? r.fulfill({ status: 503, json: { detail: "temporary_failure" } })
      : r.continue();
  });
  await p.goto(base + "visit");
  await p.getByRole("button", { name: "重新加载套餐" }).waitFor();
  await p.getByRole("button", { name: "重新加载套餐" }).click();
  await p.getByRole("button", { name: "重新加载套餐" }).waitFor();
  assert.equal(catalogs, 2);
  assert.equal(await p.locator(".time-chip").count(), 0);
  assert(!/CA\$0(?:\.00)?/.test(await p.locator("main").innerText()));
  failCatalog = false;
  await p.getByRole("button", { name: "重新加载套餐" }).click();
  await expect(p.locator(".plan-option")).toHaveCount(3);
  await p.locator(".time-chip").first().waitFor();
  assert(catalogs >= 3);
  await p.locator("input[name=guests]").fill("2");
  await p.locator("select[name=duration]").selectOption("180");
  await expect(p.locator(".visit-total strong")).toHaveText("CA$48.00");
  let failSlots = true;
  await p.route("**/studio-api/availability?*", (r) =>
    failSlots
      ? r.fulfill({ status: 503, json: { detail: "temporary_failure" } })
      : r.continue(),
  );
  await p.locator("input[name=guests]").fill("3");
  await p.locator(".slot-results .form-error").waitFor();
  failSlots = false;
  await p
    .locator(".slot-results")
    .getByRole("button", { name: "重试", exact: true })
    .click();
  await p.locator(".time-chip").first().waitFor();
  await expect(p.locator("input[name=guests]")).toHaveValue("3");
  await expect(p.locator("select[name=duration]")).toHaveValue("180");
  await expect(p.locator(".visit-total strong")).toHaveText("CA$72.00");
  await p.screenshot({ path: out + "/catalog-recovered.png", fullPage: true });
  results.push({
    finding: "F01",
    catalogRequests: catalogs,
    consecutiveFailureSafe: true,
    slotRecoveryPreservesChoices: true,
  });
  await p.close();

  // F03: explicit metric intents override stale filters; ordinary navigation keeps them.
  const desk = await browser.newPage({
    viewport: { width: 1440, height: 900 },
  });
  captureErrors(desk);
  await desk.addInitScript(() =>
    sessionStorage.setItem("puppy-studio-admin", "local-qa"),
  );
  const orderRequests = [];
  desk.on("request", (r) => {
    if (r.url().includes("/studio-api/manage/orders?"))
      orderRequests.push(new URL(r.url()).searchParams);
  });
  await desk.goto(base + "manage?view=orders");
  await desk.getByRole("button", { name: "待付款", exact: true }).click();
  await desk
    .getByRole("textbox", { name: "搜索订单或顾客" })
    .fill("old filter");
  await desk.getByRole("button", { name: "今日概览", exact: true }).click();
  await desk.locator(".desk-metric").nth(2).click();
  await expect(
    desk.getByRole("button", { name: "已收款", exact: true }),
  ).toHaveAttribute("aria-pressed", "true");
  await expect(
    desk.getByRole("textbox", { name: "搜索订单或顾客" }),
  ).toHaveValue("");
  await expect(desk.getByLabel("日期类型", { exact: true })).toHaveValue(
    "paid",
  );
  await desk.waitForTimeout(400);
  assert.equal(orderRequests.at(-1).get("status"), "received");
  assert.equal(orderRequests.at(-1).get("day_kind"), "paid");
  assert(orderRequests.at(-1).get("day"));
  await desk.getByRole("button", { name: "今日概览", exact: true }).click();
  await desk.locator(".desk-metric").nth(1).click();
  await expect(desk.getByLabel("日期类型", { exact: true })).toHaveValue(
    "created",
  );
  await desk.getByRole("button", { name: "今日概览", exact: true }).click();
  await desk.locator(".desk-metric").nth(3).click();
  await expect(desk.getByLabel("交付状态", { exact: true })).toHaveValue(
    "confirmed",
  );
  await expect(
    desk.locator(".order-secondary-filters input[type=date]"),
  ).toHaveValue("");
  await desk.getByRole("button", { name: "待付款", exact: true }).click();
  await desk.getByRole("button", { name: "今日概览", exact: true }).click();
  await desk.getByRole("button", { name: "订单管理", exact: true }).click();
  await expect(
    desk.getByRole("button", { name: "待付款", exact: true }),
  ).toHaveAttribute("aria-pressed", "true");
  results.push({
    finding: "F03",
    paidDateIntent: true,
    creationDateIntent: true,
    fulfillmentIntent: true,
    ordinaryNavigationPreservesFilters: true,
  });

  // F04 / F06: actual rendered fonts and placement, not font-family strings alone.
  await desk.getByRole("button", { name: "今日概览", exact: true }).click();
  await desk.evaluate(() => document.fonts.ready);
  await desk.waitForTimeout(400);
  const cdp = await desk.context().newCDPSession(desk);
  await cdp.send("DOM.enable");
  await cdp.send("CSS.enable");
  const doc = await cdp.send("DOM.getDocument");
  const node = await cdp.send("DOM.querySelector", {
    nodeId: doc.root.nodeId,
    selector: ".desk-welcome h1",
  });
  const fonts = (
    await cdp.send("CSS.getPlatformFontsForNode", { nodeId: node.nodeId })
  ).fonts;
  assert(
    fonts.some((f) => f.isCustomFont && f.familyName === "PinDou Sans SC"),
  );
  assert(!fonts.some((f) => f.familyName === "SimSun"));
  const recent = await desk.locator(".recent-orders").boundingBox();
  assert(recent.y < 650);
  assert.equal(await desk.locator(".desk-welcome-photo").count(), 0);
  assert.equal(await desk.locator(".setup-checklist").count(), 0);
  await desk.screenshot({
    path: out + "/overview-desktop.png",
    fullPage: true,
  });
  results.push({
    finding: "F04/F06",
    fonts,
    recentOrdersTop: recent.y,
    completedSetupCollapsed: true,
  });
  await desk.close();

  // F09: click the shell outside the visual switch track and measure real targets.
  const mobile = await browser.newPage({
    viewport: { width: 390, height: 844 },
    isMobile: true,
    hasTouch: true,
  });
  captureErrors(mobile);
  await mobile.addInitScript(() =>
    sessionStorage.setItem("puppy-studio-admin", "local-qa"),
  );
  await mobile.goto(base + "manage?view=products");
  const language = await mobile.locator(".desk-language").boundingBox();
  assert(language.width >= 44 && language.height >= 44);
  await mobile.locator(".desk-product-row").first().click();
  await mobile.locator(".studio-drawer[open]").waitFor();
  const toggle = mobile.getByRole("switch").first();
  await toggle.scrollIntoViewIfNeeded();
  const switchBox = await toggle.boundingBox();
  assert(switchBox.width >= 44 && switchBox.height >= 44);
  const track = await toggle.locator(".switch-track").boundingBox();
  assert.equal(track.height, 26);
  const was = await toggle.getAttribute("aria-checked");
  await toggle.click({ position: { x: 4, y: 3 } });
  assert.notEqual(await toggle.getAttribute("aria-checked"), was);
  await mobile.keyboard.press("Escape");
  await expect(mobile.locator(".studio-drawer[open]")).toHaveCount(0);
  results.push({
    finding: "F09",
    language,
    switchBox,
    trackHeight: track.height,
    outerShellClickable: true,
  });
  await mobile.close();

  // F10: clipboard refusal and product-catalog retry have a usable next step.
  const copy = await browser.newPage({ viewport: { width: 390, height: 844 } });
  captureErrors(copy);
  await copy.addInitScript(() =>
    Object.defineProperty(navigator, "clipboard", {
      configurable: true,
      value: { writeText: () => Promise.reject(new Error("denied")) },
    }),
  );
  await copy.goto(base);
  await copy.locator(".copy-contact").click();
  await expect(copy.locator(".manual-contact")).toBeVisible();
  await expect(copy.locator(".manual-contact span")).toHaveText(
    "xiaogoushuangji",
  );
  let productFail = true,
    attempts = 0;
  await copy.route("**/studio-api/catalog", (r) => {
    attempts++;
    return productFail
      ? r.fulfill({ status: 503, json: { detail: "temporary_failure" } })
      : r.continue();
  });
  await copy.goto(base + "shop");
  await copy.getByRole("button", { name: "重新加载商品" }).waitFor();
  productFail = false;
  await copy.getByRole("button", { name: "重新加载商品" }).click();
  await expect(copy.locator(".product-card")).toHaveCount(4);
  assert.equal(attempts, 2);
  results.push({
    finding: "F10",
    manualCopyAvailable: true,
    productRetryRequests: attempts,
  });
  await copy.close();

  // F07 / F08 / F11: real press-release frames and visible, bounded transitions.
  const motion = await browser.newPage({
    viewport: { width: 1440, height: 900 },
  });
  captureErrors(motion);
  await motion.goto(base);
  await motion.evaluate(() => document.fonts.ready);
  await motion.waitForTimeout(1700);
  const button = motion.locator(".hero-buttons .button-primary");
  await button.evaluate((el) =>
    el.addEventListener(
      "click",
      (e) => {
        e.preventDefault();
        window.qaClicks = (window.qaClicks || 0) + 1;
      },
      { capture: true },
    ),
  );
  await button.hover();
  await motion.waitForTimeout(350);
  await motion.mouse.down();
  await motion.waitForTimeout(35);
  const releaseY = await button.evaluate(
    (el) => new DOMMatrixReadOnly(getComputedStyle(el).transform).m42,
  );
  await motion.mouse.up();
  const frames = await button.evaluate(
    (el) =>
      new Promise((resolve) => {
        const r = [],
          start = performance.now();
        function frame() {
          r.push({
            t: performance.now() - start,
            y: new DOMMatrixReadOnly(getComputedStyle(el).transform).m42,
            latched: el.hasAttribute("data-pressed"),
          });
          if (performance.now() - start < 400) requestAnimationFrame(frame);
          else resolve(r);
        }
        frame();
      }),
  );
  assert(frames.every((f) => !f.latched));
  assert(
    Math.max(...frames.map((f) => f.y)) <= releaseY + 0.1,
    "button must not keep descending after release",
  );
  assert.equal(await motion.evaluate(() => window.qaClicks), 1);
  results.push({ finding: "F07", releaseY, frames });
  // Repeat entry with recording started before a scroll-triggered note becomes visible.
  await motion.reload();
  const beadFrames = await motion.evaluate(
    () =>
      new Promise((resolve) => {
        const note = document.querySelector(".hero-footnote");
        note.scrollIntoView({ block: "center" });
        const data = [],
          start = performance.now();
        function frame() {
          const bead = note.querySelector("i");
          data.push({
            t: performance.now() - start,
            parent: Number(getComputedStyle(note).opacity),
            bead: Number(getComputedStyle(bead).opacity),
          });
          if (performance.now() - start < 1400) requestAnimationFrame(frame);
          else resolve(data);
        }
        frame();
      }),
  );
  const assembling = beadFrames.filter((f) => f.bead > 0.03 && f.bead < 0.95);
  assert(assembling.length > 0);
  assert(
    assembling.every((f) => f.parent > 0.98),
    "assembly must happen after the parent is visible",
  );
  results.push({
    finding: "F08",
    visibleAssemblyFrames: assembling.length,
    minimumParentOpacity: Math.min(...assembling.map((f) => f.parent)),
  });
  await motion.locator(".photo-tile").first().click();
  await motion.waitForTimeout(750);
  const [photoStart, photoTotal] = (
    await motion.locator(".photo-controls > span").innerText()
  )
    .split("/")
    .map((s) => Number(s.trim()));
  let maximum = 1;
  for (let i = 0; i < 5; i++) {
    await motion.getByRole("button", { name: "下一张", exact: true }).click();
    await motion.waitForTimeout(50);
    maximum = Math.max(
      maximum,
      await motion.locator(".photo-stage figure").count(),
    );
  }
  assert(maximum <= 2);
  await motion.waitForTimeout(650);
  assert.equal(await motion.locator(".photo-stage figure").count(), 1);
  assert(
    await motion
      .locator(".photo-current img")
      .evaluate((e) => e.complete && e.naturalWidth > 0),
  );
  await expect(motion.locator(".photo-controls > span")).toHaveText(
    `${((photoStart - 1 + 5) % photoTotal) + 1} / ${photoTotal}`,
  );
  await motion.getByRole("button", { name: "上一张", exact: true }).click();
  await motion.waitForTimeout(50);
  await motion.getByRole("button", { name: "下一张", exact: true }).click();
  await motion.waitForTimeout(650);
  assert.equal(await motion.locator(".photo-stage figure").count(), 1);
  await motion.keyboard.press("Escape");
  await expect(motion.locator(".photo-dialog[open]")).toHaveCount(0);
  assert.equal(await motion.evaluate(() => document.body.style.position), "");
  results.push({
    finding: "F11",
    maximumLayers: maximum,
    reversalSettles: true,
    scrollRestored: true,
  });
  await motion.close();
} finally {
  await browser.close();
  await writeFile(
    out + "/functional.json",
    JSON.stringify({ results, errors }, null, 2),
  );
}
console.log(
  JSON.stringify({ passed: results.map((r) => r.finding), errors }, null, 2),
);
assert.equal(errors.length, 0);
