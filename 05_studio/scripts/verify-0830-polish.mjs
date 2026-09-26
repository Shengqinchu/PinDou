import { chromium, webkit, expect } from "@playwright/test";
import assert from "node:assert/strict";
import { mkdir, writeFile } from "node:fs/promises";
const base = "http://127.0.0.1:5184/studio/";
const engine = process.env.STUDIO_BROWSER === "webkit" ? "webkit" : "chromium";
const out =
  "../artifacts/studio-0830-polish" + (engine === "webkit" ? "-webkit" : "");
await mkdir(out, { recursive: true });
const browser = await { chromium, webkit }[engine].launch({ headless: true });
const results = [],
  errors = [];
function track(page) {
  page.on("pageerror", (e) => errors.push(e.message));
  return page;
}
try {
  // A true touch release must return to idle even while the browser retains :hover.
  for (const copyFails of [false, true]) {
    const touch = track(
      await browser.newPage({
        viewport: { width: 390, height: 844 },
        isMobile: true,
        hasTouch: true,
      }),
    );
    await touch.addInitScript(
      (copyFails) =>
        Object.defineProperty(navigator.clipboard, "writeText", {
          value: async () => {
            if (copyFails) throw new DOMException("Denied", "NotAllowedError");
          },
        }),
      copyFails,
    );
    await touch.route("**/studio-api/catalog", async (route) => {
      const response = await route.fetch(),
        catalog = await response.json();
      catalog.checkout_ready = false;
      await route.fulfill({ response, json: catalog });
    });
    await touch.goto(base + "visit");
    const contact = touch.locator(".visit-closed .button-primary");
    await contact.waitFor();
    const idle = await contact.evaluate(
      (e) => getComputedStyle(e).backgroundColor,
    );
    await contact.tap();
    await touch.waitForTimeout(400);
    const released = await contact.evaluate((e) => ({
      color: getComputedStyle(e).backgroundColor,
      active: e.matches(":active"),
      hover: e.matches(":hover"),
    }));
    assert.equal(released.color, idle);
    assert.equal(released.active, false);
    if (copyFails)
      await expect(
        touch.locator('.visit-closed [role="status"]'),
      ).toContainText("长按");
    else await expect(contact).toContainText("已复制");
    results.push({ check: "touch-release", copyFails, idle, released });
    await touch.close();
  }

  // Same-view navigation must release inertness, scroll lock and focus.
  const mobile = track(
    await browser.newPage({
      viewport: { width: 390, height: 844 },
      isMobile: true,
      hasTouch: true,
    }),
  );
  await mobile.addInitScript(() =>
    sessionStorage.setItem("puppy-studio-admin", "local-qa"),
  );
  await mobile.goto(base + "manage?view=products");
  await mobile.locator(".desk-product-row").first().waitFor();
  await mobile.locator(".desk-menu-button").tap();
  await expect(mobile.locator(".desk-sidebar")).toHaveClass(/expanded/);
  assert(await mobile.locator(".desk-main").evaluate((e) => e.inert));
  await mobile.locator(".desk-navigation > button.active").tap();
  await expect(mobile.locator(".desk-sidebar")).not.toHaveClass(/expanded/);
  assert.equal(
    await mobile.locator(".desk-main").evaluate((e) => e.inert),
    false,
  );
  assert.notEqual(
    await mobile.evaluate(() => getComputedStyle(document.body).position),
    "fixed",
  );
  await expect(mobile.locator(".desk-menu-button")).toBeFocused();
  results.push({
    check: "same-view-menu",
    menuClosed: true,
    mainInteractive: true,
    focusRestored: true,
  });
  await mobile.close();

  const desk = track(
    await browser.newPage({ viewport: { width: 1440, height: 900 } }),
  );
  await desk.addInitScript(() =>
    sessionStorage.setItem("puppy-studio-admin", "local-qa"),
  );
  await desk.goto(base + "manage");
  await desk.locator(".desk-metric").first().waitFor();
  const frames = await desk.evaluate(async () => {
    const content = document.querySelector(".desk-content"),
      indicator = document.querySelector(".desk-nav-indicator");
    const result = [],
      start = performance.now();
    document.querySelectorAll(".desk-navigation > button")[3].click();
    while (performance.now() - start < 450) {
      await new Promise(requestAnimationFrame);
      const c = getComputedStyle(content),
        n = getComputedStyle(indicator);
      result.push({
        t: performance.now() - start,
        y: c.transform === "none" ? 0 : new DOMMatrix(c.transform).m42,
        opacity: Number(c.opacity),
        nav: n.transform,
        ease: n.transitionTimingFunction,
      });
    }
    return result;
  });
  assert(frames.length > 8 && frames.every((f) => Math.abs(f.y) < 0.01));
  assert(frames.some((f) => f.opacity < 0.999));
  assert.match(frames.at(-1).ease, /0.42, 0, 0.58, 1/);
  await desk.goto(base + "manage?view=orders");
  await desk.getByLabel("订单类型", { exact: true }).waitFor();
  results.push({
    check: "stationary-desk-switch",
    frames,
    chineseOrderType: true,
  });
  await desk.close();

  // Reverse inside a visible crossfade, then sample the same layer as it fades out.
  const photos = track(
    await browser.newPage({ viewport: { width: 1440, height: 900 } }),
  );
  await photos.goto(base);
  await photos.locator(".photo-tile").first().click();
  await photos.waitForTimeout(750);
  const originalCounter = await photos
    .locator(".photo-controls > span")
    .innerText();
  for (const threshold of [0.22, 0.48, 0.72]) {
    const reverse = await photos.evaluate(async (threshold) => {
      document.querySelector('[aria-label="下一张"]').click();
      const deadline = performance.now() + 5000;
      let layer;
      while (performance.now() < deadline) {
        await new Promise(requestAnimationFrame);
        layer = document.querySelector(".photo-incoming");
        if (layer && Number(getComputedStyle(layer).opacity) >= threshold)
          break;
      }
      if (!layer) throw new Error("No visible crossfade");
      const before = Number(getComputedStyle(layer).opacity),
        start = performance.now(),
        frames = [];
      document.querySelector('[aria-label="上一张"]').click();
      while (performance.now() - start < 500) {
        await new Promise(requestAnimationFrame);
        frames.push({
          t: performance.now() - start,
          connected: layer.isConnected,
          opacity: layer.isConnected
            ? Number(getComputedStyle(layer).opacity)
            : null,
          layers: document.querySelectorAll(".photo-stage figure").length,
        });
      }
      return { before, frames };
    }, threshold);
    const early = reverse.frames.find((f) => f.t >= 15);
    assert(early.connected && early.opacity > 0);
    assert(early.opacity <= reverse.before + 0.002);
    assert(reverse.frames.filter((f) => f.connected).length >= 4);
    assert(reverse.frames.every((f) => f.layers <= 2));
    assert.equal(
      await photos.locator(".photo-controls > span").innerText(),
      originalCounter,
    );
    results.push({
      check: "continuous-photo-reversal",
      threshold,
      ...reverse,
      finalCounter: originalCounter,
    });
  }
  await photos.keyboard.press("Escape");
  await photos.close();

  for (const lang of ["zh", "en"]) {
    const p = track(await browser.newPage());
    await p.addInitScript(
      (lang) => localStorage.setItem("puppy-studio-language", lang),
      lang,
    );
    await p.route("**/studio-api/catalog", (route) => route.abort("failed"));
    for (const page of ["shop", "visit"]) {
      await p.goto(base + page);
      const message =
        lang === "zh"
          ? "暂时连接不上，请检查网络后重试。"
          : "We could not connect. Check your connection and try again.";
      await expect(p.locator("main")).toContainText(message);
      assert.doesNotMatch(
        await p.locator("main").innerText(),
        /Failed to fetch|NetworkError|Load failed/,
      );
      results.push({ check: "network-copy", lang, page, message });
    }
    await p.close();
  }

  for (const width of [320, 390, 1080, 1440]) {
    const p = track(
      await browser.newPage({ viewport: { width, height: 900 } }),
    );
    for (const [route, selector] of [
      ["", ".hero-description"],
      ["visit", ".visit-intro p"],
    ]) {
      await p.goto(base + route);
      await p.evaluate(() => document.fonts.ready);
      await p.waitForTimeout(1700);
      const lines = await p.locator(selector).evaluate((el) => {
        const walker = document.createTreeWalker(el, NodeFilter.SHOW_TEXT),
          lines = new Map();
        let node;
        while ((node = walker.nextNode())) {
          for (let i = 0; i < node.textContent.length; i++) {
            const char = node.textContent[i];
            if (/\s/.test(char)) continue;
            const range = document.createRange();
            range.setStart(node, i);
            range.setEnd(node, i + 1);
            const rect = range.getBoundingClientRect(),
              y = Math.round(rect.top);
            lines.set(y, (lines.get(y) || "") + char);
          }
        }
        return [...lines.values()];
      });
      assert(
        lines.length > 0 && lines.at(-1).length >= 4,
        JSON.stringify({ route, width, lines }),
      );
      if (width === 1080 || width === 1440)
        await p.screenshot({
          path: out + "/" + (route || "home") + "-" + width + ".png",
        });
      results.push({ check: "chinese-line-end", route, width, lines });
    }
    await p.close();
  }
  assert.deepEqual(errors, []);
} finally {
  await writeFile(
    out + "/results.json",
    JSON.stringify({ results, errors }, null, 2),
  );
  await browser.close();
}
console.log(JSON.stringify({ checks: results.length, errors, passed: true }));
