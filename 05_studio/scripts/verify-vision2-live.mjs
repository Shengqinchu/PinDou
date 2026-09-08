// Public production verification. Does not submit a reservation or an order.
import { chromium, expect } from "@playwright/test";
import assert from "node:assert/strict";
import { mkdir, writeFile } from "node:fs/promises";
const base = "https://pindoupuppy.com/studio/",
  out = "../artifacts/studio-vision2/live";
await mkdir(out, { recursive: true });
const browser = await chromium.launch({ headless: true, channel: "msedge" });
const results = [],
  errors = [];
try {
  for (const width of [390, 1440]) {
    const context = await browser.newContext({
      viewport: { width, height: 900 },
    });
    const p = await context.newPage();
    p.on("pageerror", (e) => errors.push(e.message));
    await p.goto(base + "?vision=2-20260908", { waitUntil: "networkidle" });
    await expect(p.locator("h1")).toContainText("全新拼豆手作体验");
    const build = await p
      .locator('meta[name="studio-build"]')
      .getAttribute("content");
    const versionResponse = await p.request.get(base + "version.json");
    assert.equal((await versionResponse.json()).build, build);
    assert.match(versionResponse.headers()["cache-control"], /no-store/);
    await expect(p.locator(".vision-update")).toHaveCount(0);
    assert.equal(await p.locator(".bag-button").count(), 0);
    assert.equal(await p.locator(".vision-hero-photo img").count(), 1);
    await p.waitForTimeout(1500);
    await p.screenshot({ path: out + "/home-" + width + ".png" });
    results.push({ page: "home", width, build });
    await p.getByRole("button", { name: "切换为英文", exact: true }).click();
    await expect(p.locator(".vision-brand .puppy-brandmark")).toHaveAttribute("aria-label", "Pindo Puppy");
    await expect(p.locator(".vision-brand img").last()).toHaveAttribute("src", /logo-en/);
    await p
      .getByRole("button", { name: "Switch to Chinese", exact: true })
      .click();
    for (const route of ["visit", "details", "shop", "journal", "journal/69ee262d0000000013020400", "manage"]) {
      await p.goto(base + route, { waitUntil: "networkidle" });
      if (route === "visit") {
        await p.locator(".reservation-grid").waitFor();
        const r = await p.request.get(
          "https://pindoupuppy.com/studio-api/reservation-calendar",
        );
        const calendar = await r.json();
        assert.equal(calendar.days.length, 14);
        assert.equal(calendar.max_guests_per_group, 4);
        assert(calendar.days.every(day=>day.close === "22:00"));
        await p.locator('input[value="hourly"]').check();
        await expect(p.locator(".reservation-plan-price")).toContainText("8.88");
        assert(await p.locator(".reservation-grid-scroll").evaluate(e=>e.scrollWidth<=e.clientWidth+1));
        assert.equal(
          await p.locator(".visit-total,.time-chip,.inquiry-form").count(),
          0,
        );
        const cookie = (await context.cookies()).find(
          (c) => c.name === "puppy_reservation_session",
        );
        assert(cookie?.secure && cookie?.httpOnly);
      }
      if (route === "shop")
        await expect(p.locator("main")).toContainText("尚在开发，敬请期待。");
      if (route === "details") {
        assert.equal(
          await p.locator(".vision-parking-photos figure").count(),
          2,
        );
        assert.equal(await p.locator('a[href*="google.com/maps"]').count(), 3);
      }
      if (route === "journal") assert.equal(await p.locator(".journal-story").count(), 19);
      if (route.startsWith("journal/")) assert.equal(await p.locator(".journal-entry-photos img").count(), 15);
      if (route === "manage")
        await expect(
          p.getByRole("heading", { name: "你好，店主。", exact: true }),
        ).toBeVisible();
      assert(
        await p.evaluate(
          () => document.documentElement.scrollWidth <= innerWidth + 1,
        ),
      );
      await p.screenshot({ path: out + "/" + route.replaceAll("/","-") + "-" + width + ".png" });
      results.push({ page: route, width, overflow: false });
    }
    await p.goto(base + "cart");
    await expect(p).toHaveURL(/\/studio\/shop$/);
    await p.goto("https://pindoupuppy.com/upload", {
      waitUntil: "networkidle",
    });
    await expect(p.locator("#app")).not.toBeEmpty();
    const sw = await p.evaluate(async () =>
      navigator.serviceWorker
        ? (await navigator.serviceWorker.getRegistrations()).map((r) => r.scope)
        : [],
    );
    results.push({
      page: "legacy-generator",
      width,
      rendered: true,
      serviceWorkerScopes: sw,
    });
    await context.close();
  }
  assert.deepEqual(errors, []);
} finally {
  await writeFile(
    out + "/results.json",
    JSON.stringify({ results, errors }, null, 2),
  );
  await browser.close();
}
console.log(JSON.stringify({ checks: results.length, errors }));
