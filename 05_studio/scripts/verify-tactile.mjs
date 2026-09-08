// Run against the isolated loopback QA service, never a merchant session.
import { chromium, firefox, webkit, expect } from "@playwright/test";
import assert from "node:assert/strict";
import fs from "node:fs";

const base = "http://127.0.0.1:5184/studio/";
const out = "../artifacts/studio-tactile";
fs.mkdirSync(out, { recursive: true });
const results = [],
  errors = [];
const matrix = (e) => {
  const style = getComputedStyle(e),
    m = new DOMMatrix(style.transform);
  return {
    y: m.m42,
    scale: m.a,
    shadow: style.boxShadow,
    effects: e.getAnimations().filter((a) => a.id === "studio-press-feedback")
      .length,
  };
};
async function sample(page, element, action, duration = 450) {
  const run = element.evaluate(
    (e, duration) =>
      new Promise((resolve) => {
        const rows = [],
          start = performance.now();
        function take() {
          const style = getComputedStyle(e),
            m = new DOMMatrix(style.transform);
          rows.push({
            t: performance.now() - start,
            y: m.m42,
            scale: m.a,
            effects: e
              .getAnimations()
              .filter((a) => a.id === "studio-press-feedback").length,
          });
          if (performance.now() - start < duration) requestAnimationFrame(take);
          else resolve(rows);
        }
        requestAnimationFrame(take);
      }),
    duration,
  );
  await action();
  return run;
}
async function prepare(page, route, selector) {
  await page.goto(base + route);
  const element = page.locator(selector).first();
  await element.waitFor();
  await element.scrollIntoViewIfNeeded();
  await page.mouse.move(2, 2);
  await page.waitForTimeout(350);
  return element;
}
function noQueue(frames) {
  assert(
    frames.every((f) => f.effects <= 1),
    "Press effects piled up",
  );
  assert.equal(
    frames.at(-1).effects,
    0,
    "Finished press effect remains active",
  );
}
for (const [engine, launcher] of [
  ["chromium", chromium],
  ["firefox", firefox],
  ["webkit", webkit],
]) {
  const browser = await launcher.launch({ headless: true });
  try {
    const context = await browser.newContext({
      viewport: { width: 1440, height: 900 },
      reducedMotion: "no-preference",
    });
    await context.addInitScript(() =>
      sessionStorage.setItem("puppy-studio-admin", "local-qa"),
    );
    const page = await context.newPage();
    page.on("pageerror", (e) => errors.push({ engine, message: e.message }));
    for (const [route, selector, hoverY, pressY] of [
      ["", ".vision-hero-actions .button-primary", -2, 3],
      ["visit", ".reservation-plans > label", -4, -1],
      ["journal", ".journal-story-link", -4, -1],
      ["manage", ".reservation-desk-metrics > button", -4, -1],
      ["manage", ".reservation-desk .desk-button", -2, 3],
      [
        "manage?view=reservation-calendar",
        ".reservation-desk-days button",
        -1,
        1,
      ],
    ]) {
      const el = await prepare(page, route, selector),
        box = await el.boundingBox();
      const enter = await sample(page, el, () =>
        page.mouse.move(box.x + box.width / 2, box.y + box.height / 2),
      );
      assert(
        Math.abs(enter.at(-1).y - hoverY) < 0.03,
        selector + " has no card/control lift",
      );
      assert(
        enter.some((f) => f.y < -0.1 && f.y > hoverY + 0.1),
        selector + " skipped intermediate hover frames",
      );
      // Observe native dispatch without causing navigation or a form write.
      await el.evaluate((e) => {
        window.__clicks = [];
        e.addEventListener(
          "click",
          (event) => {
            window.__clicks.push(performance.now());
            event.preventDefault();
            event.stopImmediatePropagation();
          },
          { capture: true },
        );
      });
      await page.mouse.down();
      await page.waitForTimeout(350);
      assert(
        Math.abs((await el.evaluate(matrix)).y - pressY) < 0.04,
        selector + " hover overrode active",
      );
      const release = await sample(page, el, () => page.mouse.up());
      assert(
        release.some(
          (f) => f.t > 60 && f.t < 250 && Math.abs(f.y - hoverY) > 0.12,
        ),
        "Held press snapped back",
      );
      await page.mouse.down();
      await page.waitForTimeout(45);
      const tap = await sample(page, el, () => page.mouse.up());
      assert(
        Math.max(...tap.map((f) => f.y)) > pressY - 0.35,
        "Short tap has no visible compression",
      );
      assert(
        tap.some((f) => f.t > 120 && f.t < 240 && Math.abs(f.y - hoverY) > 0.2),
        "Short tap returned instantly",
      );
      noQueue(tap);
      assert(Math.abs(tap.at(-1).y - hoverY) < 0.04);
      assert.equal(
        await page.evaluate(() => window.__clicks.length),
        2,
        "Click dispatch was swallowed or duplicated",
      );
      results.push({ engine, selector, enter, release, tap });
    }
    const button = await prepare(
      page,
      "",
      ".vision-hero-actions .button-primary",
    );
    await button.hover();
    await button.evaluate((e) =>
      e.addEventListener(
        "click",
        (event) => {
          event.preventDefault();
          event.stopImmediatePropagation();
        },
        { capture: true },
      ),
    );
    await page.mouse.down();
    await page.waitForTimeout(45);
    await page.mouse.up();
    await page.waitForTimeout(80);
    const from = (await button.evaluate(matrix)).y;
    await page.mouse.down();
    const to = (await button.evaluate(matrix)).y;
    assert(
      Math.abs(to - from) < 0.8,
      "Repeated press jumped to the CSS endpoint",
    );
    await page.waitForTimeout(35);
    const interrupted = await sample(
      page,
      button,
      async () => {
        await page.mouse.up();
        await page.waitForTimeout(65);
        await page.mouse.move(1, 1);
      },
      650,
    );
    noQueue(interrupted);
    assert(
      Math.abs(interrupted.at(-1).y) < 0.04,
      "Pointer leave retained the hover endpoint",
    );
    // Disabled mid-response must stop motion immediately and suppress activation.
    await page.goto(base + "manage");
    const disable = page.locator(".reservation-desk .desk-button").first();
    await disable.waitFor();
    await disable.hover();
    await disable.evaluate((e) => {
      window.__activationLog = [];
      e.addEventListener(
        "click",
        (event) => {
          window.__activationLog.push(performance.now());
          event.preventDefault();
          event.stopImmediatePropagation();
        },
        { capture: true },
      );
    });
    await page.mouse.down();
    await page.waitForTimeout(35);
    await page.mouse.up();
    await disable.evaluate((e) => (e.disabled = true));
    await page.waitForTimeout(30);
    assert.deepEqual(
      await disable.evaluate((e) => ({
        y: new DOMMatrix(getComputedStyle(e).transform).m42,
        effects: e
          .getAnimations()
          .filter((a) => a.id === "studio-press-feedback").length,
      })),
      { y: 0, effects: 0 },
    );
    await disable.evaluate((e) => (e.disabled = false));
    // Keyboard still operates a real button once, while the visual response finishes.
    await page.mouse.move(1, 1);
    await disable.focus();
    const beforeKeys = await page.evaluate(() => window.__activationLog.length);
    await page.keyboard.down("Space");
    await page.waitForTimeout(45);
    const keyboard = await sample(page, disable, () =>
      page.keyboard.up("Space"),
    );
    assert(Math.max(...keyboard.map((f) => f.y)) > 2.5);
    noQueue(keyboard);
    assert.equal(
      await page.evaluate(() => window.__activationLog.length),
      beforeKeys + 1,
      "Space activation was swallowed or duplicated",
    );
    // Enter produces its native activation on keydown; it is never rescheduled.
    await page.keyboard.press("Enter");
    assert.equal(
      await page.evaluate(() => window.__activationLog.length),
      beforeKeys + 2,
      "Enter activation was delayed or duplicated",
    );
    await page.waitForTimeout(400);
    await page.emulateMedia({ reducedMotion: "reduce" });
    const reduced = await sample(page, disable, () => disable.click());
    assert(
      reduced.every((f) => f.y === 0 && f.effects === 0),
      "Reduced motion still moves",
    );
    results.push({ engine, interrupted, keyboard, reduced });
    await context.close();
    if (engine !== "firefox") {
      const touch = await browser.newContext({
        viewport: { width: 390, height: 844 },
        hasTouch: true,
        isMobile: true,
        userAgent:
          "Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 Mobile/15E148 MicroMessenger/8.0.54",
      });
      await touch.addInitScript(() =>
        sessionStorage.setItem("puppy-studio-admin", "local-qa"),
      );
      const p = await touch.newPage();
      p.on("pageerror", (e) =>
        errors.push({ engine, touch: true, message: e.message }),
      );
      await p.goto(base + "manage");
      const el = p.locator(".reservation-desk .desk-button").first();
      await el.waitFor();
      await el.scrollIntoViewIfNeeded();
      await el.evaluate((e) =>
        e.addEventListener(
          "click",
          (event) => {
            event.preventDefault();
            event.stopImmediatePropagation();
          },
          { capture: true },
        ),
      );
      const frames = await sample(p, el, () => el.tap());
      noQueue(frames);
      assert(
        Math.max(...frames.map((f) => f.y)) > 2.5,
        "Touch pointerout cancelled the press response",
      );
      assert(Math.abs(frames.at(-1).y) < 0.04, "Touch left a floating control");
      assert(!(await el.evaluate((e) => e.matches(":active"))));
      const metric = p.locator(".reservation-desk-metrics > button").first();
      await metric.evaluate((e) =>
        e.addEventListener(
          "click",
          (event) => {
            event.preventDefault();
            event.stopImmediatePropagation();
          },
          { capture: true },
        ),
      );
      const metricFrames = await sample(p, metric, () => metric.tap());
      assert(
        Math.max(...metricFrames.map((f) => f.y)) > 0.75,
        "Touch card does not depress",
      );
      assert(Math.abs(metricFrames.at(-1).y) < 0.04);
      noQueue(metricFrames);
      await p.goto(base + "visit");
      await p.locator(".reservation-grid").waitFor();
      await p.locator("input[value=day]").check();
      await expect(p.locator(".reservation-day-prices")).toContainText("129.9");
      await p.goto(base + "manage");
      await p.locator(".desk-menu-button").click();
      await p.locator(".desk-navigation > button.active").click();
      await p.waitForTimeout(750);
      assert.equal(await p.locator(".desk-main").getAttribute("inert"), null);
      await p.screenshot({ path: `${out}/touch-${engine}.png` });
      results.push({ engine, touch: true, frames, menuRestored: true });
      await touch.close();
    }
    console.log(engine + " tactile checks passed");
  } finally {
    await browser.close();
  }
}
fs.writeFileSync(
  out + "/verification.json",
  JSON.stringify({ results, errors }, null, 2),
);
assert.deepEqual(errors, []);
console.log(JSON.stringify({ groups: results.length, errors }));
