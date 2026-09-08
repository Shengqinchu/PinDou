import { chromium, firefox, webkit, expect } from "@playwright/test";
import assert from "node:assert/strict";
import { mkdir, writeFile } from "node:fs/promises";
const base = "http://127.0.0.1:5184/studio/";
const out = "../artifacts/studio-0830-fixes";
await mkdir(out, { recursive: true });
const records = [],
  failures = [];
const sizes = [
  [320, 568],
  [390, 844],
  [768, 1024],
  [1080, 665],
  [1440, 900],
  [2048, 1017],
];
for (const [engineName, engine] of [
  ["chromium", chromium],
  ["webkit", webkit],
  ["firefox", firefox],
]) {
  const b = await engine.launch({ headless: true });
  try {
    for (const [width, height] of engineName === "chromium"
      ? sizes
      : [
          [390, 844],
          [1440, 900],
        ]) {
      for (const lang of ["zh", "en"]) {
        const context = await b.newContext({
          viewport: { width, height },
          reducedMotion: "reduce",
        });
        await context.addInitScript((lang) => {
          localStorage.setItem("puppy-studio-locale", lang);
          sessionStorage.setItem("puppy-studio-admin", "local-qa");
        }, lang);
        const p = await context.newPage();
        p.on("pageerror", (e) =>
          failures.push({ engineName, width, lang, error: e.message }),
        );
        let closed = false;
        await p.route("**/studio-api/catalog", async (r) => {
          const response = await r.fetch();
          const catalog = await response.json();
          catalog.products
            .filter((x) => x.kind === "physical")
            .forEach((item, i) => {
              item.zh =
                i === 0
                  ? "给喜欢慢慢创作的你准备的一整套拼豆工具与收纳配件"
                  : item.zh;
              item.en =
                i === 0
                  ? "A thoughtful set of bead tools and storage for your next colourful afternoon"
                  : item.en;
            });
          if (closed) {
            catalog.checkout_ready = false;
            catalog.settings.enabled = false;
            catalog.settings.capacity = 0;
            catalog.settings.tax_mode = "unconfirmed";
          }
          await r.fulfill({ json: catalog });
        });
        await p.goto(base + "shop");
        await p.locator(".product-card").first().waitFor();
        await p.evaluate(() => document.fonts.ready);
        const product = await p.evaluate(() => ({
          width: innerWidth,
          scroll: document.documentElement.scrollWidth,
          titles: [...document.querySelectorAll(".product-heading h2")].map(
            (e) => ({
              size: parseFloat(getComputedStyle(e).fontSize),
              width: e.getBoundingClientRect().width,
              scroll: e.scrollWidth,
            }),
          ),
          badges: [...document.querySelectorAll(".product-status")].map(
            (e) => ({
              height: e.getBoundingClientRect().height,
              bottom: getComputedStyle(e).bottom,
            }),
          ),
        }));
        assert(product.scroll <= width + 1);
        assert(
          product.titles.every(
            (t) =>
              t.size <= (width <= 600 ? 16 : 18) && t.scroll <= t.width + 1,
          ),
        );
        assert(product.badges.every((b) => b.height <= 38));
        await p.screenshot({
          path: `${out}/${engineName}-shop-${width}-${lang}.png`,
          fullPage: true,
        });
        records.push({
          finding: "F02/F12",
          engineName,
          width,
          lang,
          ...product,
        });
        await p.goto(base + "visit");
        await p.locator(".plan-option").first().waitFor();
        const planTop = await p
          .locator(".plan-option")
          .first()
          .evaluate((e) => e.getBoundingClientRect().top);
        if (width === 390)
          assert(
            planTop < 700,
            "first plan must be available in the initial phone viewport",
          );
        await p.screenshot({
          path: `${out}/${engineName}-visit-open-${width}-${lang}.png`,
        });
        closed = true;
        await p.reload();
        await p.locator(".visit-closed").waitFor();
        assert.equal(await p.locator(".time-chip,.plan-option").count(), 0);
        const statusTop = await p
          .locator(".visit-closed")
          .evaluate((e) => e.getBoundingClientRect().top);
        const action = await p.locator(".visit-closed .button").boundingBox();
        if (width === 390)
          assert(
            action.y + action.height <= height,
            "closed-state next step must be visible without completing empty selectors",
          );
        await p.screenshot({
          path: `${out}/${engineName}-visit-closed-${width}-${lang}.png`,
        });
        records.push({
          finding: "F05",
          engineName,
          width,
          lang,
          planTop,
          statusTop,
          closedActionBottom: action.y + action.height,
        });
        // Real header targets, including the narrowest 320px arrangement.
        const targets = await p
          .locator(".header-actions a,.header-actions button")
          .evaluateAll((els) =>
            els
              .filter((e) => e.getClientRects().length)
              .map((e) => ({
                name: e.getAttribute("aria-label"),
                x: e.getBoundingClientRect().x,
                right: e.getBoundingClientRect().right,
                width: e.getBoundingClientRect().width,
                height: e.getBoundingClientRect().height,
              })),
          );
        if (width <= 600) {
          assert(targets.every((t) => t.width >= 44 && t.height >= 44));
          assert(targets.every((t) => t.x >= 0 && t.right <= width));
        }
        records.push({ finding: "F09", engineName, width, lang, targets });
        await p.goto(base + "manage?view=products");
        await p.locator(".desk-product-row").first().click();
        await p.locator(".studio-drawer[open]").waitFor();
        const zh = p.getByRole("textbox", {
          name: lang === "zh" ? "中文名称" : "Chinese name",
          exact: true,
        });
        const en = p.getByRole("textbox", {
          name: lang === "zh" ? "英文名称" : "English name",
          exact: true,
        });
        await zh.fill("给喜欢慢慢创作的你准备的一整套拼豆工具与收纳配件");
        await en.fill(
          "A thoughtful set of bead tools and storage for your next colourful afternoon",
        );
        const fields = [await zh.boundingBox(), await en.boundingBox()];
        if (width <= 600)
          assert(
            fields[1].y > fields[0].y + fields[0].height,
            "phone names must have separate rows",
          );
        assert(
          await p.evaluate(
            () => document.documentElement.scrollWidth <= innerWidth + 1,
          ),
        );
        await p.screenshot({
          path: `${out}/${engineName}-editor-${width}-${lang}.png`,
        });
        records.push({
          finding: "F04/F09",
          engineName,
          width,
          lang,
          nameFields: fields,
        });
        await p.keyboard.press("Escape");
        await expect(p.locator(".studio-drawer[open]")).toHaveCount(0);
        await context.close();
        console.log(`${engineName} ${width} ${lang}: checked`);
      }
    }
  } catch (e) {
    failures.push({ engineName, message: e.stack });
    console.error(e.message);
  } finally {
    await b.close();
  }
}
await writeFile(
  out + "/layout.json",
  JSON.stringify({ records, failures }, null, 2),
);
console.log(JSON.stringify({ records: records.length, failures }, null, 2));
assert.equal(failures.length, 0);
