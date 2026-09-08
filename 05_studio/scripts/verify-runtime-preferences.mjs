// Exercise classic scrollbars and native media preferences, not video defaults.
import { chromium, webkit, expect } from "@playwright/test";
import assert from "node:assert/strict";
import fs from "node:fs";
const base = "http://127.0.0.1:5184/studio/";
const out = "../artifacts/studio-runtime-fix";
fs.mkdirSync(out, { recursive: true });
const results = [],
  errors = [];
async function position(page) {
  return page.evaluate(() => {
    const rect = document
      .querySelector(".vision-hero-photo")
      .getBoundingClientRect();
    return {
      x: rect.x,
      y: rect.y,
      width: rect.width,
      body: document.body.getBoundingClientRect().width,
      scroll: scrollY,
      client: document.documentElement.clientWidth,
      inner: innerWidth,
    };
  });
}
async function menu(page) {
  const before = await position(page);
  await page
    .getByRole("button", { name: "网站菜单", exact: true })
    .evaluate((e) => e.click());
  await page.waitForTimeout(120);
  const open = await position(page);
  for (const key of ["x", "y", "width"])
    assert(Math.abs(before[key] - open[key]) < 0.1, "Menu changed " + key);
  await page.getByRole("button", { name: "关闭菜单", exact: true }).click();
  await page.waitForTimeout(650);
  const closed = await position(page);
  for (const key of ["x", "y", "width", "scroll"])
    assert(
      Math.abs(before[key] - closed[key]) < 0.1,
      "Menu restore changed " + key,
    );
  return { before, open, closed };
}
for (const [name, engine, launch] of [
  [
    "classic-chromium",
    chromium,
    {
      ignoreDefaultArgs: ["--hide-scrollbars"],
      args: ["--disable-features=OverlayScrollbar"],
    },
  ],
  ["webkit", webkit, {}],
]) {
  const browser = await engine.launch({ headless: true, ...launch });
  try {
    const context = await browser.newContext({
      viewport: { width: 2105, height: 1193 },
      reducedMotion: null,
    });
    const page = await context.newPage();
    page.on("pageerror", (e) => errors.push({ name, message: e.message }));
    await page.goto(base + "?motion=system");
    await page.evaluate(() => document.fonts.ready);
    await page.waitForTimeout(1500);
    const native = await page.evaluate(
      () => matchMedia("(prefers-reduced-motion:reduce)").matches,
    );
    assert.equal(
      await page.locator("html").getAttribute("data-motion"),
      native ? "reduced" : "full",
    );
    if (name === "classic-chromium")
      assert(
        (await position(page)).inner - (await position(page)).client > 0,
        "Classic-scrollbar precondition missing",
      );
    const nativeMenu = await menu(page);
    await page.goto(base + "?motion=full");
    await page.evaluate(() => document.fonts.ready);
    await page.waitForTimeout(1500);
    const fullMenu = await menu(page);
    await page.evaluate(() => scrollTo(0, 700));
    const scrolledMenu = await menu(page);
    await page.evaluate(() => scrollTo(0, 0));
    await page.getByRole("button", { name: "网站菜单", exact: true }).click();
    await page.waitForTimeout(100);
    await page.setViewportSize({ width: 1080, height: 665 });
    await page.waitForTimeout(100);
    const resizedOpen = await position(page);
    await page.getByRole("button", { name: "关闭菜单", exact: true }).click();
    await page.waitForTimeout(650);
    const resizedClosed = await position(page);
    assert(Math.abs(resizedOpen.x - resizedClosed.x) < 0.1);
    assert.equal(resizedOpen.body, resizedClosed.body);
    await page.setViewportSize({ width: 1440, height: 900 });
    // Even with an OS reduction request, a deliberate site override must work.
    await page.emulateMedia({ reducedMotion: "reduce" });
    await page.goto(base + "visit");
    await page.locator(".reservation-grid").waitFor();
    assert.equal(
      await page.locator("html").getAttribute("data-motion"),
      "full",
    );
    assert.equal(
      await page.locator("html").getAttribute("data-system-motion"),
      "reduced",
    );
    const plan = page.locator(".reservation-plans > label").first();
    await plan.hover();
    await page.waitForTimeout(350);
    assert.equal(
      await plan.evaluate(
        (e) => new DOMMatrix(getComputedStyle(e).transform).m42,
      ),
      -4,
    );
    await page.locator("input[value=hourly]").check();
    await page.waitForTimeout(90);
    const price = await page
      .locator(".plan-price-reveal")
      .first()
      .evaluate((e) => ({
        height: e.getBoundingClientRect().height,
        content: e.firstElementChild.getBoundingClientRect().height,
      }));
    assert(
      price.height > 0 && price.height < price.content,
      "Full-mode price opened instantly",
    );
    await page.reload();
    await page.locator(".reservation-grid").waitFor();
    assert.equal(
      await page.locator("html").getAttribute("data-motion"),
      "full",
    );
    // Returning to system behavior is explicit and removes the saved override.
    await page.goto(base + "visit?motion=system");
    await page.locator(".reservation-grid").waitFor();
    assert.equal(
      await page.locator("html").getAttribute("data-motion"),
      "reduced",
    );
    assert.equal(
      await page.evaluate(() => localStorage.getItem("puppy-studio-motion")),
      null,
    );
    await plan.hover();
    await page.waitForTimeout(100);
    assert.equal(
      await plan.evaluate(
        (e) => new DOMMatrix(getComputedStyle(e).transform).m42,
      ),
      0,
    );
    // Per-site choices synchronize across this browser's tabs without losing forms.
    await page.getByLabel("客人名称", { exact: false }).fill("保留的测试草稿");
    const other = await context.newPage();
    await other.goto(base + "?motion=full");
    await expect(page.locator("html")).toHaveAttribute("data-motion", "full");
    assert.equal(
      await page.getByLabel("客人名称", { exact: false }).inputValue(),
      "保留的测试草稿",
    );
    await other.goto(base + "?motion=reduced");
    await expect(page.locator("html")).toHaveAttribute(
      "data-motion",
      "reduced",
    );
    await other.close();
    await page.screenshot({ path: `${out}/${name}-final.png` });
    results.push({
      name,
      native,
      nativeMenu,
      fullMenu,
      scrolledMenu,
      resizedOpen,
      resizedClosed,
      price,
      persisted: true,
      crossTab: true,
    });
    await context.close();
  } finally {
    await browser.close();
  }
}
fs.writeFileSync(
  out + "/verification.json",
  JSON.stringify({ results, errors }, null, 2),
);
assert.deepEqual(errors, []);
console.log(
  JSON.stringify({
    results: results.map((r) => ({
      name: r.name,
      nativeReduced: r.native,
      menuShift: r.fullMenu.open.x - r.fullMenu.before.x,
      scrolledShift: r.scrolledMenu.open.x - r.scrolledMenu.before.x,
      price: r.price,
      persisted: r.persisted,
    })),
    errors,
  }),
);
