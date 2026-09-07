import { chromium, expect } from "@playwright/test";
import { readFile, mkdir, writeFile } from "node:fs/promises";
import { randomBytes, randomUUID } from "node:crypto";
import assert from "node:assert/strict";
const base = "http://127.0.0.1:5184";
const output = "../artifacts/studio-desk";
await mkdir(output, { recursive: true });
const browser = await chromium.launch({ headless: true, channel: "msedge" });
const axe = await readFile("node_modules/axe-core/axe.min.js", "utf8");
const results = [];
const errors = [];
async function scan(page, label) {
  await page.evaluate(() => document.fonts.ready);
  await page.waitForTimeout(
    new URL(page.url()).pathname === "/studio/" ? 1400 : 420,
  );
  await page.addScriptTag({ content: axe });
  const audit = await page.evaluate(() =>
    axe.run(document, {
      runOnly: { type: "tag", values: ["wcag2a", "wcag2aa", "wcag21aa"] },
    }),
  );
  const dimensions = await page.evaluate(() => ({
    width: innerWidth,
    scroll: document.documentElement.scrollWidth,
  }));
  await page.evaluate(() => {
    document.activeElement?.blur();
    scrollTo({ top: 0, behavior: "instant" });
  });
  await page.screenshot({ path: `${output}/${label}.png`, fullPage: true });
  results.push({
    label,
    ...dimensions,
    violations: audit.violations.map((v) => ({
      id: v.id,
      nodes: v.nodes.map((n) => ({
        target: n.target,
        summary: n.failureSummary,
      })),
    })),
  });
}
async function seed(page) {
  const tomorrow = new Date(Date.now() + 86400000).toISOString().slice(0, 10);
  for (const [i, name] of [
    "LOCAL QA · May",
    "LOCAL QA · Jamie",
    "LOCAL QA · 小林",
  ].entries()) {
    const items =
      i === 2
        ? [{ product_id: "starter", quantity: 1 }]
        : [
            {
              product_id: "hourly",
              quantity: 1,
              booking: {
                date: tomorrow,
                start: i === 0 ? "14:00" : "16:00",
                end: i === 0 ? "16:00" : "18:00",
                guests: i === 0 ? 2 : 1,
              },
            },
          ];
    const quoteResponse = await page.request.post(
      base + "/studio-api/cart/quote",
      { data: { items } },
    );
    assert.equal(quoteResponse.status(), 200);
    const quote = await quoteResponse.json();
    const response = await page.request.post(base + "/studio-api/orders", {
      data: {
        items,
        name,
        contact_method: "wechat",
        contact: "local-qa-only",
        consent: true,
        quote_id: quote.quote_id,
        access_key: randomBytes(32).toString("hex"),
      },
      headers: { "Idempotency-Key": randomUUID() },
    });
    assert.equal(response.status(), 201);
    const order = await response.json();
    if (i !== 1)
      await page.request.post(base + "/studio-api/qa/paid/" + order.id);
  }
}
try {
  const context = await browser.newContext({
    viewport: { width: 1440, height: 1000 },
  });
  await context.addInitScript(() =>
    sessionStorage.setItem("puppy-studio-admin", "local-qa"),
  );
  const page = await context.newPage();
  page.on("pageerror", (e) => errors.push(e.message));
  await seed(page);
  await page.goto(base + "/studio/manage");
  await page.locator(".desk-metric").first().waitFor();
  await scan(page, "overview-desktop");
  await page.getByRole("button", { name: "订单管理", exact: true }).click();
  await page.locator(".desk-table tbody tr").first().waitFor();
  await scan(page, "orders-desktop");
  await page.getByRole("textbox", { name: "搜索订单或顾客" }).fill("Jamie");
  await expect(page.locator(".desk-table tbody tr")).toHaveCount(1);
  await page.getByRole("button", { name: "清除搜索", exact: true }).click();
  await expect(page.locator(".desk-table tbody tr")).toHaveCount(3);
  await page.locator(".customer-link").first().click();
  await page.locator(".studio-drawer[open]").waitFor();
  await scan(page, "order-drawer-desktop");
  await page.keyboard.press("Escape");
  await expect(page.locator(".studio-drawer")).toHaveCount(0);
  assert.equal(await page.evaluate(() => document.body.style.overflow), "");
  await page.getByRole("button", { name: "商品与体验", exact: true }).click();
  await scan(page, "products-desktop");
  await page
    .locator(".desk-product-row")
    .filter({ hasText: "给第一幅作品的工具" })
    .click();
  await page
    .getByRole("textbox", { name: "中文名称", exact: true })
    .fill("LOCAL QA · 新的小工具");
  await page.keyboard.press("Escape");
  await expect(page.locator(".studio-drawer")).toHaveCount(0);
  await page
    .locator(".desk-product-row")
    .filter({ hasText: "给第一幅作品的工具" })
    .click();
  await expect(
    page.getByRole("textbox", { name: "中文名称", exact: true }),
  ).toHaveValue("LOCAL QA · 新的小工具");
  await scan(page, "product-drawer-desktop");
  await page.getByRole("button", { name: "保存商品", exact: true }).click();
  await expect(page.locator(".studio-drawer")).toHaveCount(0);
  await page.getByRole("button", { name: "到店排班", exact: true }).click();
  await page.locator('input[name="capacity"]').fill("6");
  await page.getByRole("button", { name: "收款设置", exact: true }).click();
  await page.getByRole("button", { name: "到店排班", exact: true }).click();
  await expect(page.locator('input[name="capacity"]')).toHaveValue("6");
  await scan(page, "schedule-desktop");
  await page
    .locator(".desk-schedule")
    .getByRole("button", { name: "保存设置", exact: true })
    .click();
  await expect(
    page.locator(".desk-schedule").getByText("所有修改已保存", { exact: true }),
  ).toBeVisible();
  await page.getByRole("button", { name: "收款设置", exact: true }).click();
  await scan(page, "checkout-desktop");
  await page.getByRole("button", { name: "操作记录", exact: true }).click();
  await page.locator(".activity-row").first().waitFor();
  await scan(page, "activity-desktop");
  const button = page
    .locator(".desk-page-heading .desk-button")
    .filter({ visible: true })
    .first();
  const computed = await button.evaluate((el) => ({
    parent: getComputedStyle(el).transitionDuration,
    icon: getComputedStyle(el.querySelector("svg")).transitionDuration,
    ease: getComputedStyle(el).transitionTimingFunction,
  }));
  assert(computed.parent.includes("0.3s") && computed.icon.includes("0.3s"));
  results.push({ motion: "shared control timing", ...computed });
  await context.close();
  for (const [width, height, lang, motion] of [
    [390, 844, "zh", "no-preference"],
    [1080, 665, "en", "no-preference"],
    [2048, 1017, "zh", "reduce"],
  ]) {
    const ctx = await browser.newContext({
      viewport: { width, height },
      reducedMotion: motion,
    });
    await ctx.addInitScript((locale) => {
      sessionStorage.setItem("puppy-studio-admin", "local-qa");
      localStorage.setItem("puppy-studio-locale", locale);
    }, lang);
    const p = await ctx.newPage();
    p.on("pageerror", (e) => errors.push(e.message));
    for (const view of [
      "overview",
      "orders",
      "schedule",
      "products",
      "checkout",
    ]) {
      await p.goto(
        base + "/studio/manage" + (view === "overview" ? "" : "?view=" + view),
      );
      await p.locator(".desk-metric").first().waitFor({ state: "attached" });
      await p.waitForFunction(
        () =>
          !!document.querySelector(".desk-content .desk-page-heading") ||
          !!document.querySelector(".desk-metric"),
      );
      await scan(p, `${view}-${width}-${lang}-${motion}`);
    }
    if (width === 390) {
      await p.getByRole("button", { name: "打开后台导航" }).click();
      await scan(p, "navigation-mobile");
      await p.getByRole("button", { name: "商品与体验", exact: true }).click();
      await p.locator(".desk-product-row").first().click();
      await p.locator(".studio-drawer[open]").waitFor();
      await scan(p, "product-drawer-mobile");
      await p.keyboard.press("Escape");
      await expect(p.locator(".studio-drawer")).toHaveCount(0);
    }
    await p.goto(base + "/studio/");
    await scan(p, `home-${width}-${lang}-${motion}`);
    await p.goto(base + "/studio/shop");
    await p.locator(".product-card").first().waitFor();
    await scan(p, `shop-${width}-${lang}-${motion}`);
    await ctx.close();
  }
  const loginContext = await browser.newContext({
    viewport: { width: 1440, height: 900 },
  });
  const login = await loginContext.newPage();
  await login.goto(base + "/studio/manage");
  await scan(login, "login-desktop");
  await loginContext.close();
  await writeFile(
    output + "/results.json",
    JSON.stringify({ results, errors }, null, 2),
  );
  console.log(
    JSON.stringify(
      {
        screens: results.filter((r) => r.label).length,
        errors,
        issues: results
          .filter((r) => r.violations?.length || r.scroll > r.width + 1)
          .map((r) => ({
            label: r.label,
            overflow: r.scroll > r.width + 1,
            violations: r.violations.map((v) => ({
              id: v.id,
              nodes: v.nodes.map((n) => n.target),
            })),
          })),
      },
      null,
      2,
    ),
  );
  assert.equal(errors.length, 0, errors.join("\n"));
} finally {
  await browser.close();
}
