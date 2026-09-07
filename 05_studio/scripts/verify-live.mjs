import { chromium, expect } from "@playwright/test";
import { mkdir, writeFile } from "node:fs/promises";
import path from "node:path";

const out = path.resolve("../artifacts/studio-qa");
await mkdir(out, { recursive: true });
const browser = await chromium.launch({ headless: true, channel: "msedge" });
const result = [];
try {
  for (const [name, width, height] of [
    ["desktop", 1440, 1050],
    ["mobile", 390, 844],
  ]) {
    const context = await browser.newContext({
      viewport: { width, height },
      reducedMotion: "no-preference",
    });
    const page = await context.newPage();
    const errors = [];
    page.on("pageerror", (e) => errors.push(e.message));
    await page.goto("https://pindoupuppy.com/studio/", {
      waitUntil: "networkidle",
    });
    await expect(
      page.getByRole("heading", { name: /留一点时间/ }),
    ).toBeVisible();
    await page.waitForTimeout(1300);
    await page.screenshot({ path: path.join(out, `live-${name}-zh.png`) });
    await page.getByRole("button", { name: "Switch to English" }).click();
    await page.screenshot({ path: path.join(out, `live-${name}-en.png`) });
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth + 1,
      ),
    ).toBe(true);
    await expect(
      page.getByRole("heading", { name: /A little time/ }),
    ).toBeVisible();
    if (name === "mobile") {
      await page.getByRole("button", { name: "Navigation menu" }).click();
      await page
        .getByRole("navigation", { name: "Mobile navigation" })
        .getByRole("link", { name: "The studio", exact: true })
        .click();
      await expect(
        page.getByRole("navigation", { name: "Mobile navigation" }),
      ).not.toBeVisible();
    }
    await page.goto("https://pindoupuppy.com/studio/manage", {
      waitUntil: "networkidle",
    });
    await expect(
      page.getByRole("heading", { name: "Host sign-in", exact: true }),
    ).toBeVisible();
    await page.goto("https://pindoupuppy.com/upload", {
      waitUntil: "domcontentloaded",
    });
    await expect(page.locator("#app")).not.toBeEmpty();
    result.push({
      viewport: name,
      languages: ["zh", "en"],
      animation: "rendered",
      manager: "sign-in required",
      legacyGenerator: "rendered",
      errors,
    });
    expect(errors).toEqual([]);
    await context.close();
  }
} finally {
  await writeFile(
    path.join(out, "live-browser-results.json"),
    JSON.stringify(result, null, 2),
  );
  await browser.close();
}
console.log(JSON.stringify(result, null, 2));
