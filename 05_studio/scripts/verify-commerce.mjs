import { chromium } from "@playwright/test";
import { readFile, mkdir, writeFile } from "node:fs/promises";
import assert from "node:assert/strict";
const origin = "http://127.0.0.1:5184";
const output = "../artifacts/studio-commerce";
await mkdir(output, { recursive: true });
const browser = await chromium.launch({ headless: true, channel: "msedge" });
const axe = await readFile("node_modules/axe-core/axe.min.js", "utf8");
const results = [];
async function inspect(page, label, screenshot = true) {
  await page.evaluate(() => document.fonts.ready);
  await page.waitForTimeout(400);
  await page.addScriptTag({ content: axe });
  const a11y = await page.evaluate(() =>
    axe.run(document, {
      runOnly: { type: "tag", values: ["wcag2a", "wcag2aa", "wcag21aa"] },
    }),
  );
  const overflow = await page.evaluate(() => ({
    width: innerWidth,
    scroll: document.documentElement.scrollWidth,
  }));
  await page.evaluate(() => {
    document.activeElement?.blur();
    scrollTo({ top: 0, behavior: "instant" });
  });
  if (screenshot)
    await page.screenshot({ path: `${output}/${label}.png`, fullPage: true });
  results.push({
    label,
    overflow,
    violations: a11y.violations.map((v) => ({
      id: v.id,
      impact: v.impact,
      nodes: v.nodes.map((n) => n.target),
    })),
  });
  assert(
    overflow.scroll <= overflow.width + 1,
    label + ": horizontal overflow",
  );
}
try {
  const context = await browser.newContext({
    viewport: { width: 1440, height: 1000 },
  });
  const page = await context.newPage();
  const errors = [];
  page.on("pageerror", (e) => errors.push(e.message));
  await page.goto(`${origin}/studio/visit`);
  await page.locator(".time-chip").first().waitFor();
  await page.locator(".time-chip").filter({ hasText: "14:00" }).click();
  await inspect(page, "visit-desktop");
  await page.getByRole("button", { name: "加入购物车", exact: true }).click();
  await page.getByRole("link", { name: "去结账", exact: true }).click();
  await page.locator(".payable-total").waitFor();
  assert.match(await page.locator(".payable-total").innerText(), /80\.00/);
  await page.goto(`${origin}/studio/shop`);
  await page.locator(".product-card").first().getByRole("button").click();
  await page.getByRole("link", { name: /购物车，/ }).click();
  await page.locator(".payable-total").waitFor();
  await page.getByRole("button", { name: "增加数量" }).click();
  await page.waitForFunction(() =>
    document.querySelector(".payable-total")?.textContent?.includes("200.00"),
  );
  await page.reload();
  await page.locator(".payable-total").waitFor();
  assert.equal(await page.locator(".bag-line").count(), 2);
  await page.locator('input[name="name"]').fill("Local Browser QA");
  await page.locator('input[name="contact"]').fill("local-qa-only");
  await page.locator(".consent-label input").check();
  await inspect(page, "cart-desktop");
  await page.getByRole("button", { name: "去付款", exact: true }).click();
  await page.waitForURL(/\/order\/PS/);
  await page.locator(".cashier-panel").waitFor();
  await inspect(page, "cashier-desktop-local-fixture");
  const orderId = new URL(page.url()).pathname.split("/").pop();
  await page.request.post(`${origin}/studio-api/qa/paid/${orderId}`);
  await page.getByRole("button", { name: "刷新付款状态" }).click();
  await page.locator(".order-seal.confirmed").waitFor();
  await inspect(page, "confirmed-desktop-local-fixture");
  await page.reload();
  await page.locator(".order-seal.confirmed").waitFor();
  assert.equal(errors.length, 0, errors.join("\n"));
  await context.close();

  for (const [width, lang] of [
    [360, "zh"],
    [390, "zh"],
    [768, "en"],
    [1440, "en"],
  ]) {
    const ctx = await browser.newContext({
      viewport: { width, height: 900 },
      reducedMotion: "reduce",
    });
    await ctx.addInitScript(
      (locale) => localStorage.setItem("puppy-studio-locale", locale),
      lang,
    );
    const p = await ctx.newPage();
    await p.goto(`${origin}/studio/visit`);
    await p.locator(".time-chip").first().waitFor();
    await inspect(p, `visit-${width}-${lang}`);
    await p.locator(".time-chip:not(:disabled)").last().click();
    await p.locator(".commerce-panel > button").click();
    await p.goto(`${origin}/studio/cart`);
    await p.locator(".payable-total").waitFor();
    await inspect(p, `cart-${width}-${lang}`);
    await p.goto(`${origin}/studio/shop`);
    await p.locator(".product-card").first().waitFor();
    await inspect(p, `shop-${width}-${lang}`);
    await ctx.close();
  }
  // Host workspace is covered by verify-desk-motion.mjs.
  await writeFile(
    `${output}/browser-results.json`,
    JSON.stringify(results, null, 2),
  );
  console.log(
    JSON.stringify(
      {
        checked: results.length,
        violations: results.filter((r) => r.violations.length),
        output,
      },
      null,
      2,
    ),
  );
} finally {
  await browser.close();
}
