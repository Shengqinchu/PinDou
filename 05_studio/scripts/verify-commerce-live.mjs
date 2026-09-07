// Read-only public production checks. No checkout, customer submission or payment.
import { chromium } from "@playwright/test";
import { mkdir, writeFile } from "node:fs/promises";
import assert from "node:assert/strict";
const base = "https://pindoupuppy.com";
const output = "../artifacts/studio-commerce/live";
await mkdir(output, { recursive: true });
const browser = await chromium.launch({ headless: true, channel: "msedge" });
const results = [];
try {
  for (const width of [390, 1440]) {
    const context = await browser.newContext({
      viewport: { width, height: 980 },
    });
    const page = await context.newPage();
    const errors = [];
    page.on("pageerror", (e) => errors.push(e.message));
    for (const route of ["visit", "shop", "cart", "manage"]) {
      const response = await page.goto(`${base}/studio/${route}`, {
        waitUntil: "networkidle",
      });
      assert.equal(response.status(), 200);
      assert(await page.locator("main h1").count());
      assert(
        await page.evaluate(
          () => document.documentElement.scrollWidth <= innerWidth + 1,
        ),
      );
      if (route === "visit") {
        await page
          .getByText("新的到店时段，正在安排中", { exact: true })
          .waitFor();
        assert.equal(await page.locator(".time-chip").count(), 0);
        assert.equal(await page.locator(".inquiry-form").count(), 0);
      }
      if (route === "cart")
        assert.match(await page.locator("main").innerText(), /装进购物车/);
      if (route === "shop")
        assert.equal(await page.locator(".product-card").count(), 4);
      if (route === "manage")
        await page
          .getByRole("heading", { name: "你好，店主。", exact: true })
          .waitFor();
      await page.screenshot({
        path: `${output}/${route}-${width}.png`,
        fullPage: true,
      });
      results.push({
        width,
        route,
        status: response.status(),
        overflow: false,
      });
    }
    const response = await page.request.get(base + "/studio-api/catalog");
    const data = await response.json();
    assert.equal(data.settings.fx_cny_per_cad, "5.0000");
    assert.equal(data.settings.capacity, 0);
    assert.equal(data.checkout_ready, false);
    assert.equal(data.payment_configured, true);
    assert.match(response.headers()["cache-control"], /no-store/);
    assert.deepEqual(errors, []);
    await context.close();
  }
  await writeFile(output + "/results.json", JSON.stringify(results, null, 2));
  console.log(
    JSON.stringify({
      pages: results.length,
      frontend: "live",
      checkout: "closed until business settings are confirmed",
      merchant: "configured",
      fx: "1 CAD = 5 CNY",
      errors: 0,
    }),
  );
} finally {
  await browser.close();
}
