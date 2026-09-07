import { chromium, webkit, expect } from "@playwright/test";
import assert from "node:assert/strict";
import { writeFile, mkdir } from "node:fs/promises";
const root = "http://127.0.0.1:5184";
const base = root + "/studio/";
const out = "../artifacts/studio-motion-v2";
await mkdir(out, { recursive: true });
const results = [];
for (const [engineName, engine] of [
  ["chromium", chromium],
  ["webkit", webkit],
]) {
  const browser = await engine.launch({ headless: true });
  try {
    const context = await browser.newContext({
      viewport: { width: 390, height: 844 },
      isMobile: true,
      hasTouch: true,
    });
    await context.addInitScript(() =>
      sessionStorage.setItem("puppy-studio-admin", "local-qa"),
    );
    const page = await context.newPage();
    await page.goto(base + "manage?view=schedule");
    await page.locator("input[name=capacity]").waitFor();
    await page.evaluate(() => document.fonts.ready);
    await page.waitForTimeout(750);
    await page.locator("input[name=capacity]").fill("9");
    await page.evaluate(() => scrollTo({ top: 700, behavior: "instant" }));
    await page.waitForTimeout(100);
    const before = await page.evaluate(() => scrollY);
    // Click the visible sticky control. Locator.scrollIntoViewIfNeeded can itself
    // reposition a sticky header in browser automation, before the click occurs.
    const menuBox = await page
      .getByRole("button", { name: "打开后台导航", exact: true })
      .boundingBox();
    await page.touchscreen.tap(
      menuBox.x + menuBox.width / 2,
      menuBox.y + menuBox.height / 2,
    );
    await page.waitForTimeout(740);
    assert.equal(
      await page.evaluate(() => document.body.style.position),
      "fixed",
    );
    await page.getByRole("button", { name: "商品与体验", exact: true }).click();
    await page.waitForTimeout(650);
    await page
      .getByRole("button", { name: "打开后台导航", exact: true })
      .click();
    await page.getByRole("button", { name: "到店排班", exact: true }).click();
    await page.waitForTimeout(650);
    await expect(page.locator("input[name=capacity]")).toHaveValue("9");
    assert(
      Math.abs((await page.evaluate(() => scrollY)) - before) < 3,
      "mobile menu must preserve the logical scroll position, not fixed-body scrollY=0",
    );
    results.push({
      engine: engineName,
      label: "menu-state-and-scroll",
      before,
      after: await page.evaluate(() => scrollY),
    });

    await page.goto(base + "manage?view=products");
    const product = page.locator(".desk-product-row").first();
    await product.click();
    await page.waitForTimeout(740);
    const field = page.getByRole("textbox", { name: "中文名称", exact: true });
    await field.fill("LOCAL QA · 保留草稿");
    await page.keyboard.press("Escape");
    await page.waitForTimeout(100);
    await product.evaluate((e) => e.click());
    await page.waitForTimeout(740);
    await expect(page.locator(".studio-drawer[open]")).toHaveAttribute(
      "data-phase",
      "open",
    );
    await expect(field).toHaveValue("LOCAL QA · 保留草稿");
    await page.setViewportSize({ width: 844, height: 390 });
    await page.waitForTimeout(180);
    await page.evaluate(() => {
      const s = document.documentElement.style;
      s.setProperty("--safe-left", "44px");
      s.setProperty("--safe-right", "44px");
      s.setProperty("--safe-bottom", "21px");
    });
    const bounds = await page.locator(".studio-drawer[open]").evaluate((el) => {
      const body = el.querySelector(".drawer-body"),
        foot = el.querySelector(".drawer-bottom");
      return {
        bodyRightPadding: parseFloat(getComputedStyle(body).paddingRight),
        footRightPadding: parseFloat(getComputedStyle(foot).paddingRight),
        footBottomPadding: parseFloat(getComputedStyle(foot).paddingBottom),
        viewport: innerWidth,
        fixedBody: document.body.getBoundingClientRect().width,
      };
    });
    assert(
      bounds.bodyRightPadding >= 44 &&
        bounds.footRightPadding >= 44 &&
        bounds.footBottomPadding >= 21,
      "notched landscape safe areas must protect inputs and save",
    );
    assert.equal(
      bounds.viewport,
      bounds.fixedBody,
      "locked body must resize on rotation",
    );
    await page.screenshot({
      path: `${out}/${engineName}-safe-area-landscape-emulated.png`,
    });
    await page.keyboard.press("Escape");
    await expect(page.locator(".studio-drawer[open]")).toHaveCount(0);
    assert.equal(await page.evaluate(() => document.body.style.position), "");
    results.push({
      engine: engineName,
      label: "drawer-interruption-rotation-safearea",
      ...bounds,
    });
    await context.close();

    for (const [
      name,
      userAgent,
      width,
      height,
      touch,
      platform,
      wantMobile,
    ] of [
      [
        "wechat-android-landscape",
        "Mozilla/5.0 (Linux; Android 14) AppleWebKit/537.36 Chrome/120.0.0.0 Mobile Safari/537.36 MicroMessenger/8.0.60",
        844,
        390,
        true,
        "Linux armv8l",
        true,
      ],
      [
        "ipad-desktop-identity",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15) AppleWebKit/605.1.15 Version/18.5 Safari/605.1.15",
        1024,
        768,
        true,
        "MacIntel",
        true,
      ],
      [
        "wechat-desktop",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36 MicroMessenger/8.0.1",
        1440,
        900,
        false,
        "Win32",
        false,
      ],
    ]) {
      const c = await browser.newContext({
        viewport: { width, height },
        userAgent,
        hasTouch: touch,
        isMobile: touch,
      });
      await c.addInitScript(
        ({ platform, touch }) => {
          Object.defineProperty(navigator, "platform", { value: platform });
          Object.defineProperty(navigator, "maxTouchPoints", {
            value: touch ? 5 : 0,
          });
          localStorage.setItem(
            "puppy-order-access-v2",
            JSON.stringify({ PSVIEWPORTQA: "local-presentation-only" }),
          );
        },
        { platform, touch },
      );
      const p = await c.newPage();
      const quote = await (
        await p.request.post(root + "/studio-api/cart/quote", {
          data: { items: [{ product_id: "starter", quantity: 1 }] },
        })
      ).json();
      let paid = false,
        requests = 0;
      await p.route("**/studio-api/orders/PSVIEWPORTQA", async (r) => {
        requests++;
        await r.fulfill({
          json: {
            id: "PSVIEWPORTQA",
            status: paid ? "paid" : "pending",
            created_at: Date.now() / 1000,
            expires_at: Date.now() / 1000 + 300,
            hold_until: Date.now() / 1000 + 390,
            paid_at: paid ? Date.now() / 1000 : null,
            fulfillment: "pending",
            quote,
            version: 1,
            payment_url: root + "/local-presentation-only-cashier",
            qr_url: root + "/studio-api/qa/qr",
          },
        });
      });
      await p.goto(base + "order/PSVIEWPORTQA");
      await p.locator(".cashier-panel").waitFor();
      const check = async () => {
        assert.equal(
          await p.locator(".payment-qr").count(),
          wantMobile ? 0 : 1,
          `${engineName} ${name}: correct QR presentation`,
        );
        assert.equal(
          await p
            .getByRole("link", { name: "打开虎皮椒收银台", exact: true })
            .count(),
          wantMobile ? 1 : 0,
        );
      };
      await check();
      await p.setViewportSize({ width: height, height: width });
      await check();
      const beforeRequests = requests;
      paid = true;
      await p.evaluate(() =>
        window.dispatchEvent(
          new PageTransitionEvent("pageshow", { persisted: true }),
        ),
      );
      await p.locator(".order-seal.confirmed").waitFor();
      assert(
        requests > beforeRequests,
        "return from cashier must refresh server state",
      );
      results.push({
        engine: engineName,
        label: name,
        cashier: wantMobile ? "mobile URL" : "desktop QR",
        stableAfterRotation: true,
        refreshedOnReturn: true,
        presentationFixtureOnly: true,
      });
      await c.close();
    }
  } finally {
    await browser.close();
  }
}
await writeFile(
  out + "/webview-lifecycle.json",
  JSON.stringify(results, null, 2),
);
console.log(JSON.stringify(results, null, 2));
