import { chromium, webkit } from "@playwright/test";
import assert from "node:assert/strict";
import { writeFile } from "node:fs/promises";
const checks = [];
for (const [name, engine] of [
  ["chromium", chromium],
  ["webkit", webkit],
]) {
  const b = await engine.launch({ headless: true });
  const p = await b.newPage({ viewport: { width: 1440, height: 900 } });
  await p.goto("http://127.0.0.1:5184/studio/shop");
  await p.locator(".product-card").first().waitFor();
  await p.evaluate(() => document.fonts.ready);
  await p.waitForTimeout(800);
  const original = await p.locator(".product-card").evaluateAll((els) =>
    els.map((e) => ({
      name: e.querySelector("h2").textContent,
      width: e.getBoundingClientRect().width,
      left: e.offsetLeft,
      top: e.offsetTop,
    })),
  );
  await p.getByRole("button", { name: "补充豆", exact: true }).click();
  await p.waitForTimeout(100);
  const leaving = await p
    .locator(".product-list-leave-active")
    .evaluateAll((els) =>
      els.map((e) => ({
        name: e.querySelector("h2").textContent,
        width: parseFloat(e.style.width),
        left: parseFloat(e.style.left),
        top: parseFloat(e.style.top),
      })),
    );
  assert(leaving.length > 0);
  for (const item of leaving) {
    const before = original.find((x) => x.name === item.name);
    assert(Math.abs(before.width - item.width) < 1);
    assert.equal(before.left, item.left);
    assert.equal(before.top, item.top);
  }
  await p.waitForTimeout(600);
  assert.equal(await p.locator(".product-card").count(), 1);
  await p.getByRole("button", { name: "全部", exact: true }).click();
  await p.waitForTimeout(80);
  await p.getByRole("button", { name: "工具配件", exact: true }).click();
  await p.waitForTimeout(700);
  assert(
    await p
      .locator(".product-card")
      .evaluateAll((els) => els.every((e) => !e.style.width && !e.style.left)),
  );
  checks.push({
    engine: name,
    preservedLeavingGeometry: true,
    rapidFiltering: true,
  });
  await b.close();
}
await writeFile(
  "../artifacts/studio-motion-v2/list-continuity.json",
  JSON.stringify(checks, null, 2),
);
console.log(JSON.stringify(checks));
