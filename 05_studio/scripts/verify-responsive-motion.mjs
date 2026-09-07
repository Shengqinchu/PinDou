import { chromium, webkit, firefox, expect } from "@playwright/test";
import { mkdir, writeFile, readFile } from "node:fs/promises";
import assert from "node:assert/strict";
const base = "http://127.0.0.1:5184/studio/";
const out = "../artifacts/studio-motion-v2";
await mkdir(out, { recursive: true });
const results = [],
  errors = [],
  failures = [];
const axe = await readFile("node_modules/axe-core/axe.min.js", "utf8");
const wechatUA =
  "Mozilla/5.0 (iPhone; CPU iPhone OS 18_5 like Mac OS X) AppleWebKit/605.1.15 Mobile/15E148 MicroMessenger/8.0.60 NetType/WIFI Language/zh_CN";
async function inspect(page, label, screenshot = false, accessibility = false) {
  await page.evaluate(() => document.fonts.ready);
  await page.waitForTimeout(720);
  const geometry = await page.evaluate(() => {
    const width = document.documentElement.clientWidth;
    return {
      width,
      height: innerHeight,
      scrollWidth: document.documentElement.scrollWidth,
      outside: [
        ...document.querySelectorAll(
          "main button,main input,main select,main h1,main h2,.drawer-panel",
        ),
      ]
        .filter((e) => e.getClientRects().length && !e.closest("[inert]"))
        .flatMap((e) => {
          const r = e.getBoundingClientRect();
          let parent = e.parentElement,
            insideHorizontalScroller = false;
          while (parent && parent !== document.body) {
            if (
              ["auto", "scroll"].includes(getComputedStyle(parent).overflowX) &&
              parent.scrollWidth > parent.clientWidth
            ) {
              insideHorizontalScroller = true;
              break;
            }
            parent = parent.parentElement;
          }
          return !insideHorizontalScroller &&
            (r.left < -2 || r.right > width + 2) &&
            getComputedStyle(e).visibility !== "hidden"
            ? [
                {
                  tag: e.tagName,
                  class: e.className,
                  text: e.textContent?.slice(0, 35),
                  left: r.left,
                  right: r.right,
                },
              ]
            : [];
        }),
      inputFonts: [
        ...document.querySelectorAll(
          "input:not([type=checkbox]):not([type=radio]),select,textarea",
        ),
      ]
        .filter((e) => e.getClientRects().length)
        .map((e) => parseFloat(getComputedStyle(e).fontSize)),
    };
  });
  if (geometry.scrollWidth > geometry.width + 1 || geometry.outside.length)
    failures.push({ label, ...geometry });
  if (geometry.width <= 900 && geometry.inputFonts.some((x) => x < 16))
    failures.push({ label, smallInputs: geometry.inputFonts });
  let violations = [];
  if (accessibility) {
    await page.addScriptTag({ content: axe });
    violations = await page.evaluate(async () =>
      (
        await axe.run(document, {
          runOnly: { type: "tag", values: ["wcag2a", "wcag2aa", "wcag21aa"] },
        })
      ).violations.map((v) => ({
        id: v.id,
        targets: v.nodes.map((n) => ({
          target: n.target,
          summary: n.failureSummary,
        })),
      })),
    );
    if (violations.length) failures.push({ label, violations });
  }
  results.push({ label, ...geometry, violations });
  if (screenshot)
    await page.screenshot({ path: `${out}/${label}.png`, fullPage: true });
}

for (const [name, engine] of [
  ["chromium", chromium],
  ["webkit", webkit],
  ["firefox", firefox],
]) {
  let browser;
  try {
    browser = await engine.launch({ headless: true });
    results.push({ label: "engine", name, version: browser.version() });
    const context = await browser.newContext({
      viewport: { width: 1440, height: 900 },
      reducedMotion: "reduce",
    });
    await context.addInitScript(() => {
      sessionStorage.setItem("puppy-studio-admin", "local-qa");
      localStorage.setItem(
        "puppy-shopping-bag-v2",
        JSON.stringify([
          {
            key: "responsive-qa",
            product_id: "starter",
            quantity: 1,
            booking: null,
          },
        ]),
      );
    });
    const page = await context.newPage();
    page.on("pageerror", (e) =>
      errors.push({ engine: name, message: e.message }),
    );
    const sizes =
      name === "chromium"
        ? [
            [320, 568],
            [360, 640],
            [375, 667],
            [390, 844],
            [414, 896],
            [600, 800],
            [601, 800],
            [767, 900],
            [768, 1024],
            [820, 1180],
            [859, 900],
            [860, 900],
            [899, 900],
            [900, 900],
            [901, 900],
            [1024, 768],
            [1080, 665],
            [1150, 800],
            [1190, 800],
            [1280, 720],
            [1440, 900],
            [1920, 1080],
            [2048, 1017],
            [2560, 1440],
            [3440, 1440],
            [844, 390],
            [1280, 480],
          ]
        : [
            [320, 568],
            [390, 844],
            [768, 1024],
            [1080, 665],
            [1440, 900],
            [844, 390],
          ];
    for (const [w, h] of sizes) {
      await page.setViewportSize({ width: w, height: h });
      for (const path of ["", "visit", "cart", "manage?view=schedule"]) {
        await page.goto(base + path);
        await page
          .locator(
            path.startsWith("manage")
              ? "input[name=capacity]"
              : path === "visit"
                ? ".time-chip"
                : path === "cart"
                  ? ".payable-total"
                  : ".hero",
          )
          .first()
          .waitFor();
        await inspect(
          page,
          `${name}-${w}x${h}-${path.split("?")[0] || "home"}`,
          [320, 390, 1440].includes(w),
          w === 390 || w === 1440,
        );
        if (!path && w <= 600) {
          await page
            .locator(".work-grid")
            .evaluate((e) => (e.scrollLeft = e.scrollWidth));
          const last = await page
            .locator(".work-grid .photo-tile")
            .last()
            .boundingBox();
          assert(
            last && last.x >= 0 && last.x + last.width <= w + 1,
            "last gallery tile must be reachable in its intentional scroller",
          );
        }
      }
      if (w === 390 || w === 1440 || w === 320 || h === 390) {
        await page.goto(base + "manage?view=products");
        await page.locator(".desk-product-row").first().click();
        await page.locator(".studio-drawer[open] .drawer-panel").waitFor();
        await inspect(
          page,
          `${name}-${w}x${h}-drawer`,
          true,
          w === 390 || w === 1440,
        );
        const bounds = await page
          .locator(".studio-drawer[open]")
          .evaluate((e) => {
            const header = e
                .querySelector(".drawer-top")
                .getBoundingClientRect(),
              footer = e
                .querySelector(".drawer-bottom")
                .getBoundingClientRect();
            return {
              top: header.top,
              bottom: footer.bottom,
              height: innerHeight,
            };
          });
        if (bounds.top < -1 || bounds.bottom > bounds.height + 1)
          failures.push({
            label: "drawer reachable controls",
            engine: name,
            w,
            h,
            ...bounds,
          });
        await page.keyboard.press("Escape");
        await expect(page.locator(".studio-drawer[open]")).toHaveCount(0);
      }
      console.log(`${name} ${w}x${h}: inspected`);
    }
    // Normal-motion sampling uses a fine pointer, independent of the layout audit.
    if (name === "chromium") {
      await page.setViewportSize({ width: 1440, height: 900 });
      await page.emulateMedia({ reducedMotion: "no-preference" });
      await page.goto(base + "manage");
      const metric = page.locator(".desk-metric").first();
      await metric.waitFor();
      await page.mouse.move(1400, 850);
      await page.waitForTimeout(600);
      const frame = () =>
        metric.evaluate((el) => {
          const parent = getComputedStyle(el),
            child = getComputedStyle(el.querySelector("strong"));
          return {
            y: new DOMMatrixReadOnly(parent.transform).m42,
            childY: new DOMMatrixReadOnly(child.transform).m42,
            duration: parent.transitionDuration,
            childDuration: child.transitionDuration,
          };
        });
      const frames = [];
      await metric.hover();
      let previous = 0;
      for (const ms of [100, 240, 520]) {
        await page.waitForTimeout(ms - previous);
        frames.push({ ms, ...(await frame()) });
        previous = ms;
      }
      assert(
        frames[0].y < 0 && frames[0].y > -3,
        "hover must have a visible intermediate frame",
      );
      for (const f of frames)
        assert(
          Math.abs(f.y / 3 - f.childY) < 0.06,
          "parent and nested number must advance together",
        );
      assert.equal(frames.at(-1).y, -3);
      results.push({ label: "synchronised-card-frames", frames });

      await page.goto(base);
      await page.waitForTimeout(1700);
      const button = page.locator(".hero-buttons .button-primary");
      await button.evaluate((e) =>
        e.addEventListener(
          "click",
          (ev) => {
            ev.preventDefault();
            window.qaClicks = (window.qaClicks || 0) + 1;
          },
          { capture: true },
        ),
      );
      await button.hover();
      await page.waitForTimeout(550);
      await page.mouse.down();
      await page.waitForTimeout(35);
      await page.mouse.up();
      assert.equal(
        await page.evaluate(() => window.qaClicks),
        1,
        "tap action must not be delayed",
      );
      assert(
        await button.evaluate((e) => e.hasAttribute("data-pressed")),
        "short tap must retain visible press",
      );
      await page.waitForTimeout(850);
      assert(!(await button.evaluate((e) => e.hasAttribute("data-pressed"))));
      results.push({
        label: "quick-tap",
        immediateAction: true,
        retainedPress: true,
        released: true,
      });

      await page.locator(".photo-tile").first().click();
      await page.waitForTimeout(760);
      await inspect(page, "photo-desktop", true, true);
      const stage = await page.locator(".photo-stage").boundingBox();
      await page.getByRole("button", { name: "下一张", exact: true }).click();
      await page.waitForTimeout(160);
      const during = await page.locator(".photo-stage").boundingBox();
      assert.equal(stage.height, during.height);
      assert.equal(stage.width, during.width);
      assert.equal(
        await page.locator(".photo-stage figure").count(),
        2,
        "crossfade must overlap images",
      );
      await page.screenshot({ path: `${out}/photo-crossfade-midframe.png` });
      await page.keyboard.press("Escape");
      await page.waitForTimeout(70);
      await page
        .locator(".photo-tile")
        .first()
        .evaluate((e) => e.click());
      await page.waitForTimeout(800);
      await expect(page.locator(".photo-dialog[open]")).toHaveAttribute(
        "data-phase",
        "open",
      );
      await page.keyboard.press("Escape");
      await expect(page.locator(".photo-dialog[open]")).toHaveCount(0);
      assert.equal(await page.evaluate(() => document.body.style.position), "");
      results.push({
        label: "photo-interruption",
        stableStage: true,
        interruptedCloseReopen: true,
        bodyRestored: true,
      });
    }
    await context.close();

    if (name !== "firefox") {
      const ctx = await browser.newContext({
        viewport: { width: 390, height: 844 },
        isMobile: true,
        hasTouch: true,
        userAgent: wechatUA,
      });
      await ctx.addInitScript(() => {
        sessionStorage.setItem("puppy-studio-admin", "local-qa");
        localStorage.setItem("puppy-studio-locale", "en");
        const visual = new EventTarget();
        Object.assign(visual, { height: 844, offsetTop: 0, scale: 1 });
        Object.defineProperty(window, "visualViewport", {
          value: visual,
          configurable: true,
        });
        window.qaViewport = visual;
      });
      const p = await ctx.newPage();
      p.on("pageerror", (e) =>
        errors.push({
          engine: name,
          context: "WeChat emulation",
          message: e.message,
        }),
      );
      await p.goto(base + "manage?view=products");
      await p.locator(".desk-product-row").first().click();
      await p.waitForTimeout(760);
      const field = p.getByRole("textbox", {
        name: "English name",
        exact: true,
      });
      await field.fill("LOCAL VIEWPORT QA");
      await p.evaluate(() => {
        Object.assign(window.qaViewport, { height: 360, offsetTop: 18 });
        window.qaViewport.dispatchEvent(new Event("resize"));
      });
      await p.waitForTimeout(150);
      const keyboard = await p
        .locator(".studio-drawer[open]")
        .evaluate((el) => {
          const head = el.querySelector(".drawer-top").getBoundingClientRect(),
            foot = el.querySelector(".drawer-bottom").getBoundingClientRect(),
            body = el.querySelector(".drawer-body").getBoundingClientRect(),
            input = document.activeElement.getBoundingClientRect();
          return {
            top: head.top,
            bottom: foot.bottom,
            bodyTop: body.top,
            bodyBottom: body.bottom,
            inputTop: input.top,
            inputBottom: input.bottom,
            keyboard:
              document.documentElement.classList.contains("keyboard-open"),
            safeBottom: getComputedStyle(
              document.documentElement,
            ).getPropertyValue("--safe-bottom"),
          };
        });
      assert(keyboard.keyboard && keyboard.top >= 18 && keyboard.bottom <= 379);
      if (
        keyboard.inputTop < keyboard.bodyTop ||
        keyboard.inputBottom > keyboard.bodyBottom
      )
        failures.push({ label: `${name}-keyboard-focused-field`, ...keyboard });
      await p.screenshot({
        path: `${out}/${name}-wechat-keyboard-emulated.png`,
      });
      await p.evaluate(() => {
        Object.assign(window.qaViewport, { height: 844, offsetTop: 0 });
        window.qaViewport.dispatchEvent(new Event("resize"));
      });
      await p.keyboard.press("Escape");
      await expect(p.locator(".studio-drawer[open]")).toHaveCount(0);
      await p.setViewportSize({ width: 844, height: 390 });
      await p.evaluate(() => {
        Object.assign(window.qaViewport, { height: 390, offsetTop: 0 });
        window.qaViewport.dispatchEvent(new Event("resize"));
      });
      await p.goto(base + "visit");
      await p.locator(".time-chip").first().waitFor();
      await inspect(p, `${name}-wechat-landscape-emulated`, true, false);
      results.push({ label: `${name}-wechat-keyboard-emulated`, ...keyboard });
      await ctx.close();
    }
  } catch (e) {
    failures.push({ engine: name, error: e.stack });
    console.error(name, e.message);
  } finally {
    await browser?.close();
  }
}
await writeFile(
  `${out}/results.json`,
  JSON.stringify({ results, errors, failures }, null, 2),
);
console.log(
  JSON.stringify({ checks: results.length, errors, failures }, null, 2),
);
assert.equal(
  errors.length + failures.length,
  0,
  "responsive/motion checks failed; see results.json",
);
