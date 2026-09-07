import { chromium, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
import { mkdir, writeFile } from "node:fs/promises";
import path from "node:path";

const base = process.env.STUDIO_URL || "http://127.0.0.1:5184/studio/";
const out = path.resolve("../artifacts/studio-qa");
await mkdir(out, { recursive: true });
const browser = await chromium.launch({ headless: true, channel: "msedge" });
const results = [];
try {
  for (const [name, width, height] of [
    ["desktop", 1440, 1050],
    ["mobile", 390, 844],
  ]) {
    const context = await browser.newContext({
      viewport: { width, height },
      reducedMotion: "reduce",
    });
    const page = await context.newPage();
    const errors = [];
    page.on("pageerror", (e) => errors.push(e.message));
    for (const [route, label] of [
      ["", "home"],
      ["visit", "visit"],
      ["shop", "shop"],
      ["journal", "journal"],
    ]) {
      await page.goto(base + route, { waitUntil: "networkidle" });
      await page.screenshot({
        path: path.join(out, `${name}-${label}.png`),
        fullPage: false,
      });
      if (label === "home")
        await page.screenshot({
          path: path.join(out, `${name}-home-full.png`),
          fullPage: true,
        });
      const overflow = await page.evaluate(
        () => document.documentElement.scrollWidth > innerWidth + 1,
      );
      const brokenImages = await page
        .locator("img")
        .evaluateAll((images) =>
          images
            .filter((img) => img.complete && !img.naturalWidth)
            .map((img) => img.src),
        );
      const scan = await new AxeBuilder({ page })
        .withTags(["wcag2a", "wcag2aa", "wcag21aa"])
        .analyze();
      results.push({
        viewport: name,
        route: label,
        overflow,
        brokenImages,
        violations: scan.violations.map((v) => ({
          id: v.id,
          impact: v.impact,
          nodes: v.nodes.map((n) => n.target),
        })),
      });
      expect(overflow, `${name} ${label} horizontal overflow`).toBe(false);
      expect(brokenImages, `${name} ${label} broken images`).toEqual([]);
      expect(scan.violations, `${name} ${label} accessibility issues`).toEqual(
        [],
      );
    }
    await page.goto(base + "visit");
    await page.getByLabel("你的称呼", { exact: true }).fill("本地验收测试");
    await page.getByLabel("微信号", { exact: true }).fill("studio-local-qa");
    await page.getByRole("button", { name: "Switch to English" }).click();
    await expect(page.getByLabel("Your name", { exact: true })).toHaveValue(
      "本地验收测试",
    );
    await expect(page.locator("html")).toHaveAttribute("lang", "en-CA");
    await expect(page.getByLabel("WeChat ID", { exact: true })).toHaveValue(
      "studio-local-qa",
    );
    if (!process.env.STUDIO_SKIP_SUBMIT) {
      await page.getByRole("checkbox").check();
      await page.getByRole("button", { name: "Send visit request" }).click();
      await expect(page.getByText(/VIS-[A-F0-9]{12}/)).toBeVisible();
      await page.screenshot({
        path: path.join(out, `${name}-visit-receipt.png`),
      });
    }
    await page.goto(base + "shop");
    await page
      .getByRole("button", {
        name: "Add A little more colour to your selection",
        exact: true,
      })
      .click();
    await expect(
      page.getByRole("link", { name: "Your selection, 1 items" }),
    ).toBeVisible();
    await page.reload();
    await expect(
      page.getByRole("link", { name: "Your selection, 1 items" }),
    ).toBeVisible();
    await page
      .getByRole("button", {
        name: "Increase A little more colour",
        exact: true,
      })
      .click();
    if (!process.env.STUDIO_SKIP_SUBMIT) {
      await page.getByLabel("Your name", { exact: true }).fill("Pickup QA");
      await page
        .getByLabel("WeChat ID", { exact: true })
        .fill("studio-local-qa");
      await page.getByRole("checkbox").check();
      await page.getByRole("button", { name: "Send pickup inquiry" }).click();
      await expect(page.getByText(/PUP-[A-F0-9]{12}/)).toBeVisible();
      await expect(
        page.getByRole("link", { name: "Your selection, 0 items" }),
      ).toBeVisible();
    }
    await page.goto(base + "journal");
    await page.locator(".photo-tile").first().click();
    await expect(page.getByRole("dialog")).toBeVisible();
    await page.keyboard.press("Escape");
    await expect(page.getByRole("dialog")).not.toBeVisible();
    await page.goto(base);
    await expect(page.locator('a[href="/upload"]').first()).toBeAttached();
    results.push({ viewport: name, pageErrors: errors });
    expect(errors).toEqual([]);
    await context.close();
  }
} finally {
  await writeFile(
    path.join(out, "browser-results.json"),
    JSON.stringify(results, null, 2),
  );
  await browser.close();
}
console.log(JSON.stringify(results, null, 2));
