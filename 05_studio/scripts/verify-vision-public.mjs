import { chromium, expect } from "@playwright/test";
import assert from "node:assert/strict";
import { mkdir, writeFile } from "node:fs/promises";
const base = process.env.STUDIO_BASE || "http://127.0.0.1:5184/studio/";
const out = "../artifacts/studio-vision/public";
await mkdir(out, { recursive: true });
const browser = await chromium.launch({ headless: true });
const results = [],
  errors = [];
try {
  for (const width of [320, 390, 768, 1080, 1440, 2048]) {
    for (const lang of ["zh", "en"]) {
      const p = await browser.newPage({
        viewport: { width, height: 900 },
        reducedMotion: "reduce",
      });
      p.on("pageerror", (e) => errors.push(e.message));
      await p.addInitScript(
        (lang) => localStorage.setItem("puppy-studio-locale", lang),
        lang,
      );
      for (const route of ["", "shop", "details", "journal"]) {
        await p.goto(base + route);
        await p.evaluate(() => document.fonts.ready);
        assert(
          await p.evaluate(
            () => document.documentElement.scrollWidth <= innerWidth + 1,
          ),
          route + width + lang,
        );
        assert.equal(await p.locator(".bag-button").count(), 0);
        await expect(p.locator(".vision-brand")).toHaveText(
          lang === "zh" ? "小狗拼豆铺" : "Pindo Puppy",
        );
        if (route === "") {
          assert.equal(await p.locator(".vision-hero-photo img").count(), 1);
          const photo = await p.locator(".vision-hero-photo").boundingBox(),
            actions = await p.locator(".vision-hero-actions").boundingBox();
          assert(actions.y >= photo.y + photo.height - 1);
          assert.equal(await p.locator(".vision-hero-actions a").count(), 2);
          assert.equal(
            await p.locator(".vision-carousel-window figure").count(),
            6,
          );
          await p.locator(".vision-carousel-window").focus();
          await p.keyboard.press("ArrowRight");
          await expect(
            p.locator(".vision-carousel-controls > span"),
          ).toHaveText("2 / 6");
          await p
            .getByRole("button", {
              name: lang === "zh" ? "网站菜单" : "Site menu",
              exact: true,
            })
            .click();
          await expect(p.locator(".studio-drawer")).toHaveAttribute("open", "");
          await p.locator(".vision-menu > a").first().click();
          await expect(p.locator(".studio-drawer")).not.toHaveAttribute(
            "open",
            "",
          );
          if (lang === "zh")
            assert(
              !/HAMILTON|WELCOME|OUR LITTLE|WeChat|pindou puppy|Pindo Puppy/.test(
                await p.locator("main").innerText(),
              ),
            );
        }
        if (route === "shop") {
          await expect(p.locator("main")).toContainText(
            lang === "zh"
              ? "尚在开发，敬请期待。"
              : "Still in the making. Coming soon.",
          );
          assert.equal(await p.locator(".product-card").count(), 0);
        }
        if (route === "details") {
          assert.equal(
            await p.locator(".vision-parking-photos figure").count(),
            2,
          );
          assert.equal(
            await p.locator('a[href*="google.com/maps"]').count(),
            3,
          );
          if (lang === "zh")
            assert(
              !/楼层|单元|请联系店主确认地址/.test(
                await p.locator("main").innerText(),
              ),
            );
        }
        if ([390, 1440].includes(width))
          await p.screenshot({
            path:
              out + "/" + (route || "home") + "-" + width + "-" + lang + ".png",
            fullPage: true,
          });
        results.push({ route: route || "home", width, lang, overflow: false });
      }
      await p.goto(base + "cart");
      await expect(p).toHaveURL(/\/shop$/);
      await p.close();
    }
  }
  assert.deepEqual(errors, []);
} finally {
  await writeFile(
    out + "/results.json",
    JSON.stringify({ results, errors }, null, 2),
  );
  await browser.close();
}
console.log(JSON.stringify({ pages: results.length, errors }));
