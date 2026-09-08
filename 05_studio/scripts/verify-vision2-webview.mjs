import { chromium, webkit, expect } from "@playwright/test";
import assert from "node:assert/strict";
import { mkdir, writeFile } from "node:fs/promises";
const out = "../artifacts/studio-vision2/webview";
await mkdir(out, { recursive: true });
const results = [],
  errors = [];
for (const [name, engine, ua] of [
  [
    "android-wechat",
    chromium,
    "Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Mobile Safari/537.36 MicroMessenger/8.0.50",
  ],
  [
    "ios-wechat-engine",
    webkit,
    "Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 Mobile/15E148 MicroMessenger/8.0.50",
  ],
]) {
  const browser = await engine.launch({ headless: true });
  try {
    const context = await browser.newContext({
      viewport: { width: 390, height: 844 },
      isMobile: true,
      hasTouch: true,
      userAgent: ua,
    });
    const p = await context.newPage();
    p.on("pageerror", (e) => errors.push(e.message));
    await p.goto("http://127.0.0.1:4184/studio/visit");
    await p.locator(".reservation-grid").waitFor();
    await p.locator('input[value="hourly"]').check();
    await p.getByLabel("客人名称", { exact: false }).fill("保留的预约草稿");
    await p.locator('[data-cell="1"]').tap();
    const before = await p.locator(".reservation-selection").innerText();
    await p.getByRole("button", { name: "切换为英文", exact: true }).tap();
    assert.equal(
      await p.getByLabel("Guest name", { exact: false }).inputValue(),
      "保留的预约草稿",
    );
    await p
      .getByRole("button", { name: "Switch to Chinese", exact: true })
      .tap();
    await p.getByRole("button", { name: "网站菜单", exact: true }).tap();
    await p.waitForTimeout(750);
    assert.equal(await p.evaluate(() => document.body.style.position), "fixed");
    await p.setViewportSize({ width: 844, height: 390 });
    await p.evaluate(() => {
      document.documentElement.style.setProperty("--safe-left", "44px");
      document.documentElement.style.setProperty("--safe-right", "44px");
      document.documentElement.style.setProperty("--safe-bottom", "21px");
    });
    await p.waitForTimeout(400);
    const panel = await p
      .locator(".studio-drawer[open] .drawer-panel")
      .boundingBox();
    assert(
      panel.x >= 0 &&
        panel.x + panel.width <= 844 + 1 &&
        panel.height <= 390 + 1,
    );
    await p.getByRole("button", { name: "关闭菜单", exact: true }).tap();
    await p.waitForTimeout(600);
    assert.notEqual(
      await p.evaluate(() => document.body.style.position),
      "fixed",
    );
    const header = await p
      .locator(".vision-header")
      .evaluate((e) => ({
        left: parseFloat(getComputedStyle(e).paddingLeft),
        right: parseFloat(getComputedStyle(e).paddingRight),
      }));
    assert(header.left >= 44 && header.right >= 44);
    await p.setViewportSize({ width: 390, height: 844 });
    await p.evaluate(() => {
      for (const name of ["--safe-left", "--safe-right", "--safe-bottom"])
        document.documentElement.style.removeProperty(name);
    });
    const input = p.getByLabel("客人名称", { exact: false });
    await input.focus();
    assert(
      (await input.evaluate((e) => parseFloat(getComputedStyle(e).fontSize))) >=
        16,
    );
    await p.setViewportSize({ width: 390, height: 470 });
    await input.scrollIntoViewIfNeeded();
    const box = await input.boundingBox();
    assert(box.y >= 0 && box.y + box.height <= 471);
    await p.setViewportSize({ width: 390, height: 844 });
    await p.route("**/studio/version.json", (route) =>
      route.fulfill({ json: { build: "newer-vision-build" } }),
    );
    await p.evaluate(() => window.dispatchEvent(new Event("pageshow")));
    await expect(p.locator(".vision-update")).toBeVisible();
    assert.equal(await input.inputValue(), "保留的预约草稿");
    await p.getByRole("button", { name: "重新载入", exact: true }).click();
    await p.locator(".reservation-grid").waitFor();
    assert.equal(
      await p.getByLabel("客人名称", { exact: false }).inputValue(),
      "保留的预约草稿",
    );
    assert.equal(await p.locator(".reservation-selection").innerText(), before);
    await p.screenshot({ path: out + "/" + name + ".png" });
    results.push({
      name,
      simulation: true,
      rotation: true,
      safeArea: true,
      keyboardViewport: true,
      languageDraft: true,
      versionReloadRetainsDraft: true,
    });
    await context.close();
  } finally {
    await browser.close();
  }
}
assert.deepEqual(errors, []);
await writeFile(
  out + "/results.json",
  JSON.stringify({ results, errors }, null, 2),
);
console.log(JSON.stringify({ results, errors }));
