import { chromium, webkit, firefox, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
import assert from "node:assert/strict";
import { mkdir, writeFile } from "node:fs/promises";
const out = "../artifacts/studio-vision/responsive";
await mkdir(out, { recursive: true });
const result = [],
  errors = [];
for (const [engine, type, sizes] of [
  [
    "chromium",
    chromium,
    [
      [320, 568],
      [390, 844],
      [600, 800],
      [760, 900],
      [768, 1024],
      [900, 700],
      [1080, 665],
      [1440, 900],
      [2048, 1017],
      [2560, 1440],
      [844, 390],
    ],
  ],
  [
    "webkit",
    webkit,
    [
      [390, 844],
      [1440, 900],
    ],
  ],
  [
    "firefox",
    firefox,
    [
      [390, 844],
      [1440, 900],
    ],
  ],
]) {
  const browser = await type.launch({ headless: true });
  try {
    for (const [width, height] of sizes)
      for (const lang of ["zh", "en"]) {
        const context = await browser.newContext({
          viewport: { width, height },
          reducedMotion: "no-preference",
        });
        const p = await context.newPage();
        p.on("pageerror", (e) => errors.push(engine + ":" + e.message));
        await p.addInitScript((lang) => {
          localStorage.setItem("puppy-studio-locale", lang);
          sessionStorage.setItem("puppy-studio-admin", "local-qa");
        }, lang);
        for (const route of ["visit", "manage"]) {
          await p.goto("http://127.0.0.1:5184/studio/" + route);
          await p
            .locator(
              route === "visit"
                ? ".reservation-grid"
                : ".reservation-desk-policy",
            )
            .first()
            .waitFor();
          await p.evaluate(() => document.fonts.ready);
          await p.waitForTimeout(250);
          const geometry = await p.evaluate(() => ({
            width: innerWidth,
            document: document.documentElement.scrollWidth,
            body: document.body.scrollWidth,
          }));
          assert(
            geometry.document <= width + 1,
            JSON.stringify({ engine, route, lang, geometry }),
          );
          if (route === "visit") {
            const cell = p.locator('[data-cell="1"]');
            await cell.focus();
            await p.keyboard.press("ArrowDown");
            await expect(p.locator('[data-cell="8"]')).toBeFocused();
            await p.keyboard.press("Enter");
            await expect(p.locator(".reservation-selection")).toContainText(
              "10:30–12:30",
            );
            if (width < 760)
              assert(
                await p
                  .locator(".reservation-grid-scroll")
                  .evaluate((e) => e.scrollWidth > e.clientWidth),
              );
          } else if (width <= 900) {
            await p.locator(".desk-menu-button").click();
            await p.locator(".desk-navigation > button.active").click();
            await expect(p.locator(".desk-sidebar")).not.toHaveClass(
              /expanded/,
            );
            assert.equal(
              await p.locator(".desk-main").evaluate((e) => e.inert),
              false,
            );
          }
          if (
            engine === "chromium" &&
            [390, 1440].includes(width) &&
            lang === "zh"
          ) {
            const issues = (
              await new AxeBuilder({ page: p })
                .withTags(["wcag2a", "wcag2aa"])
                .analyze()
            ).violations;
            assert.deepEqual(
              issues.map((v) => ({
                id: v.id,
                nodes: v.nodes.map((n) => n.target),
              })),
              [],
              route + " accessibility",
            );
            await p.screenshot({
              path: out + "/" + route + "-" + width + ".png",
            });
          }
          result.push({ engine, width, height, lang, route, geometry });
        }
        await context.close();
      }
  } finally {
    await browser.close();
    await writeFile(
      out + "/results.json",
      JSON.stringify({ result, errors }, null, 2),
    );
  }
}
assert.deepEqual(errors, []);
console.log(JSON.stringify({ records: result.length, errors }));
