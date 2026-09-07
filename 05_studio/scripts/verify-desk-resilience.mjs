import { chromium, expect } from "@playwright/test";
import assert from "node:assert/strict";
import { writeFile } from "node:fs/promises";
const base = "http://127.0.0.1:5184";
const browser = await chromium.launch({ headless: true, channel: "msedge" });
const result = {};
try {
  const ctx = await browser.newContext({
    viewport: { width: 390, height: 844 },
  });
  await ctx.addInitScript(() => {
    sessionStorage.setItem("puppy-studio-admin", "local-qa");
    localStorage.setItem("puppy-studio-locale", "en");
  });
  const p = await ctx.newPage();
  await p.goto(base + "/studio/manage?view=schedule");
  await p.locator('input[name="capacity"]').waitFor();
  assert(await p.locator(".desk-sidebar").evaluate((e) => e.inert));
  const fits = await p
    .locator(".weekly-setting>span")
    .evaluateAll((items) =>
      items.every((e) => e.scrollWidth <= e.clientWidth + 1),
    );
  assert(fits);
  await p.getByRole("button", { name: "Open desk navigation" }).click();
  await expect(p.locator(".desk-sidebar")).toHaveClass(/expanded/);
  for (let i = 0; i < 16; i++) await p.keyboard.press("Tab");
  assert(
    await p.evaluate(() =>
      document.querySelector(".desk-sidebar").contains(document.activeElement),
    ),
  );
  await p.keyboard.press("Escape");
  await expect(p.locator(".desk-sidebar")).not.toHaveClass(/expanded/);
  assert.equal(await p.evaluate(() => document.body.style.overflow), "");
  result.mobileNavigation =
    "hidden items inert; focus trapped; Escape restores scrolling";
  await p.goto(base + "/studio/manage?view=products");
  await p.locator(".desk-product-row").first().click();
  await p.locator(".studio-drawer[open]").waitFor();
  const name = p.getByRole("textbox", { name: "English name", exact: true });
  await name.fill("LOCAL QA · preserved after save failure");
  await p.route("**/studio-api/manage/products/*", (route) =>
    route.fulfill({
      status: 503,
      contentType: "application/json",
      body: '{"detail":"temporary_failure"}',
    }),
  );
  await p.getByRole("button", { name: "Save product", exact: true }).click();
  await p.locator(".studio-drawer[open] .desk-error").waitFor();
  await expect(name).toHaveValue("LOCAL QA · preserved after save failure");
  await expect(p.locator(".studio-drawer[open]")).toBeVisible();
  await p.unroute("**/studio-api/manage/products/*");
  await p.getByRole("button", { name: "Save product", exact: true }).click();
  await expect(p.locator(".studio-drawer[open]")).toHaveCount(0);
  result.failedSave = "draft retained; visible error; successful retry";
  await p.screenshot({
    path: "../artifacts/studio-desk/products-mobile-en.png",
    fullPage: true,
  });
  await ctx.close();
  const desktop = await browser.newContext({
    viewport: { width: 1440, height: 900 },
  });
  const page = await desktop.newPage();
  await page.goto(base + "/studio/");
  await page.waitForTimeout(1400);
  const button = page.locator(".hero-buttons .button-primary");
  await button.evaluate((el) =>
    el.addEventListener("click", (e) => e.preventDefault(), {
      once: true,
      capture: true,
    }),
  );
  const sample = () =>
    button.evaluate((el) => {
      const s = getComputedStyle(el),
        i = getComputedStyle(el.querySelector("svg"));
      return {
        transform: s.transform,
        shadow: s.boxShadow,
        duration: s.transitionDuration,
        iconDuration: i.transitionDuration,
        ease: s.transitionTimingFunction,
      };
    });
  const states = { idle: await sample() };
  await button.hover();
  await page.waitForTimeout(550);
  states.hover = await sample();
  await page.mouse.down();
  await page.waitForTimeout(550);
  states.pressed = await sample();
  await page.mouse.up();
  await page.waitForTimeout(550);
  states.released = await sample();
  assert.notEqual(states.idle.transform, states.hover.transform);
  assert.notEqual(states.hover.transform, states.pressed.transform);
  assert.equal(states.hover.transform, states.released.transform);
  assert(
    states.pressed.duration.includes("0.48s") &&
      states.pressed.iconDuration.includes("0.48s"),
  );
  result.controlStates = states;
  await desktop.close();
  await writeFile(
    "../artifacts/studio-desk/resilience.json",
    JSON.stringify(result, null, 2),
  );
  console.log(JSON.stringify(result, null, 2));
} finally {
  await browser.close();
}
