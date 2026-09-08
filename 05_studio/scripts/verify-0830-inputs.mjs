import { chromium, expect } from "@playwright/test";
import assert from "node:assert/strict";
import { writeFile } from "node:fs/promises";
const base = "http://127.0.0.1:5184/studio/";
const b = await chromium.launch({ headless: true });
const records = [];
try {
  const p = await b.newPage({ viewport: { width: 1440, height: 900 } });
  await p.goto(base);
  const button = p.locator(".copy-contact");
  await button.evaluate((el) =>
    el.addEventListener(
      "click",
      (e) => {
        e.preventDefault();
        e.stopImmediatePropagation();
        window.spaceClicks = (window.spaceClicks || 0) + 1;
      },
      { capture: true },
    ),
  );
  await button.focus();
  await p.keyboard.down("Space");
  await p.waitForTimeout(360);
  const down = await button.evaluate((e) => getComputedStyle(e).transform);
  await p.keyboard.up("Space");
  await p.waitForTimeout(360);
  const up = await button.evaluate((e) => getComputedStyle(e).transform);
  assert.notEqual(down, up);
  assert.equal(await p.evaluate(() => window.spaceClicks), 1);
  await button.dblclick();
  assert.equal(await p.evaluate(() => window.spaceClicks), 3);
  records.push({
    finding: "F07",
    keyboardDown: down,
    keyboardReleased: up,
    spaceActionOnce: true,
    doubleClickActions: 2,
  });
  await p.close();

  const touch = await b.newPage({
    viewport: { width: 390, height: 844 },
    isMobile: true,
    hasTouch: true,
  });
  await touch.goto(base + "visit");
  const chip = touch.locator(".date-chip").first();
  await chip.scrollIntoViewIfNeeded();
  await chip.evaluate((e) => {
    window.touchClicks = 0;
    window.touchCancels = 0;
    e.addEventListener("click", () => window.touchClicks++);
    e.addEventListener("pointercancel", () => window.touchCancels++);
  });
  const rect = await chip.boundingBox(),
    cdp = await touch.context().newCDPSession(touch);
  const x = rect.x + rect.width / 2,
    y = rect.y + rect.height / 2;
  await cdp.send("Input.dispatchTouchEvent", {
    type: "touchStart",
    touchPoints: [{ x, y }],
  });
  await touch.waitForTimeout(35);
  await cdp.send("Input.dispatchTouchEvent", {
    type: "touchMove",
    touchPoints: [{ x, y: y - 80 }],
  });
  await touch.waitForTimeout(30);
  await cdp.send("Input.dispatchTouchEvent", {
    type: "touchMove",
    touchPoints: [{ x, y: y - 150 }],
  });
  await cdp.send("Input.dispatchTouchEvent", {
    type: "touchEnd",
    touchPoints: [],
  });
  const canceled = await touch.evaluate(() => ({
    clicks: window.touchClicks,
    cancels: window.touchCancels,
    latched: document.querySelectorAll("[data-pressed]").length,
  }));
  assert.equal(canceled.clicks, 0);
  assert(canceled.cancels > 0);
  assert.equal(canceled.latched, 0);
  records.push({ finding: "F07", touch: canceled });
  await touch.close();

  for (const kind of ["slow", "failure"]) {
    const page = await b.newPage({ viewport: { width: 1440, height: 900 } });
    let release,
      requests = 0,
      fail = true;
    const gate = new Promise((r) => (release = r));
    await page.route("**/studio-media/journal-05.jpg", async (route) => {
      requests++;
      if (kind === "slow") await gate;
      if (kind === "failure" && fail) return route.abort("failed");
      await route.continue();
    });
    await page.goto(base, { waitUntil: "domcontentloaded" });
    await page.locator(".photo-tile").first().click();
    await page.waitForTimeout(750);
    await page.locator(".photo-current img").evaluate((e) => e.decode());
    const before = await page.locator(".photo-current img").getAttribute("src");
    await page.getByRole("button", { name: "下一张", exact: true }).click();
    await page.waitForTimeout(120);
    assert(
      await page
        .locator(".photo-current img")
        .evaluate((e) => e.complete && e.naturalWidth > 0),
    );
    assert.equal(
      await page.locator(".photo-current img").getAttribute("src"),
      before,
    );
    if (kind === "slow") release();
    else {
      await page
        .locator(".photo-load-status")
        .getByRole("button", { name: "重试", exact: true })
        .waitFor();
      fail = false;
      await page
        .locator(".photo-load-status")
        .getByRole("button", { name: "重试", exact: true })
        .click();
    }
    await expect(page.locator(".photo-controls > span")).toHaveText("3 / 6");
    assert(requests > 0);
    records.push({
      finding: "F11",
      scenario: kind,
      requests,
      previousImageRetained: true,
      eventualTarget: "3 / 6",
    });
    await page.close();
  }
} finally {
  await b.close();
}
await writeFile(
  "../artifacts/studio-0830-fixes/inputs.json",
  JSON.stringify(records, null, 2),
);
console.log(JSON.stringify(records, null, 2));
