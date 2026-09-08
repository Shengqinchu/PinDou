// Loopback QA only: submits and confirms synthetic reservations, never payments.
import { chromium, expect } from "@playwright/test";
import assert from "node:assert/strict";
import { mkdir, writeFile } from "node:fs/promises";
const base = "http://127.0.0.1:5184/studio/",
  out = "../artifacts/studio-vision/reservations";
await mkdir(out, { recursive: true });
const browser = await chromium.launch({ headless: true });
const results = [],
  errors = [];
try {
  const p = await browser.newPage({
    viewport: { width: 390, height: 844 },
    isMobile: true,
    hasTouch: true,
  });
  p.on("pageerror", (e) => errors.push(e.message));
  await p.goto(base + "visit");
  await p.locator(".reservation-grid").waitFor();
  assert.equal(
    await p.locator(".reservation-plans input[type=radio]").count(),
    2,
  );
  assert.equal(await p.locator(".reservation-credit input").count(), 0);
  const before = await p.request.get(
    "http://127.0.0.1:8011/studio-api/manage/orders",
  );
  const paidBefore = (await before.json()).total;
  await p.locator('[data-cell="1"]').click();
  await expect(p.locator(".reservation-selection")).toContainText(
    "10:00–12:00",
  );
  await p.locator('[data-cell="36"]').click(); // same day 12:30 cell extends to 13:00
  await expect(p.locator(".reservation-selection")).toContainText(
    "10:00–13:00",
  );
  await p.getByLabel("同行人数（包括你自己）", { exact: true }).fill("2");
  await p
    .getByLabel("客人名称", { exact: false })
    .fill("VISION guest " + Date.now());
  const name = await p.getByLabel("客人名称", { exact: false }).inputValue();
  await p.getByLabel("微信号", { exact: true }).fill("vision-test-only");
  await p
    .getByLabel("同意将以上信息用于本次预约联系。", { exact: true })
    .check();
  assert(
    !/CA\$|本次体验|总额|付款后|加入购物车/.test(
      await p.locator("main").innerText(),
    ),
  );
  await p.screenshot({ path: out + "/selected-mobile.png", fullPage: true });
  await p.getByRole("button", { name: "提交预约", exact: true }).click();
  await expect(p).toHaveURL(/\/reservation\/VIS-/);
  await expect(p.locator("h1")).toContainText("等待店主确认");
  const receipt = p.url(),
    ref = receipt.split("/").at(-1);
  await p.reload();
  await expect(p.locator("h1")).toContainText("等待店主确认");
  const outsider = await browser.newPage();
  assert.equal(
    (
      await outsider.request.get(
        "http://127.0.0.1:5184/studio-api/reservations/" + ref,
      )
    ).status(),
    404,
  );
  await outsider.close();
  const admin = await browser.newPage({
    viewport: { width: 1440, height: 900 },
  });
  admin.on("pageerror", (e) => errors.push(e.message));
  await admin.addInitScript(() =>
    sessionStorage.setItem("puppy-studio-admin", "local-qa"),
  );
  await admin.goto(base + "manage");
  await admin
    .locator(".reservation-desk-row")
    .filter({ hasText: name })
    .click();
  await admin
    .getByLabel("更新预约状态", { exact: true })
    .selectOption("confirmed");
  await admin
    .getByLabel("店内备注（客人不可见）", { exact: true })
    .fill("PRIVATE QA NOTE");
  await admin.getByRole("button", { name: "保存安排", exact: true }).click();
  await expect(admin.locator(".studio-drawer[open]")).toHaveCount(0);
  await p.getByRole("button", { name: "刷新预约状态", exact: true }).click();
  await expect(p.locator("h1")).toContainText("预约成功");
  assert(!(await p.locator("main").innerText()).includes("PRIVATE QA NOTE"));
  await p.screenshot({ path: out + "/confirmed-mobile.png", fullPage: true });
  await admin.screenshot({ path: out + "/desk-desktop.png", fullPage: true });
  const paidAfter = await p.request.get(
    "http://127.0.0.1:8011/studio-api/manage/orders",
  );
  assert.equal((await paidAfter.json()).total, paidBefore);
  results.push({
    flow: "submitted-reloaded-confirmed",
    ref,
    privateReceipt: true,
    noPaymentOrder: true,
  });
  await p
    .getByRole("link", { name: "拼豆铺详细信息", exact: true })
    .first()
    .click();
  await expect(p).toHaveURL(/\/details$/);
  await p.close();
  await admin.close();

  const recovery = await browser.newPage({
    viewport: { width: 1440, height: 900 },
  });
  recovery.on("pageerror", (e) => errors.push(e.message));
  await recovery.goto(base + "visit");
  await recovery.locator('[data-cell="1"]').click();
  await recovery
    .getByLabel("客人名称", { exact: false })
    .fill("VISION lost response");
  await recovery.getByLabel("微信号", { exact: true }).fill("replay-test-only");
  await recovery
    .getByLabel("同意将以上信息用于本次预约联系。", { exact: true })
    .check();
  let swallowed = false,
    original;
  await recovery.route("**/studio-api/reservations", async (route) => {
    if (route.request().method() === "POST" && !swallowed) {
      swallowed = true;
      const response = await route.fetch();
      original = await response.json();
      await route.abort("failed");
    } else await route.continue();
  });
  await recovery.getByRole("button", { name: "提交预约", exact: true }).click();
  await expect(
    recovery.getByRole("button", { name: "恢复预约结果", exact: true }),
  ).toBeEnabled();
  await recovery.reload();
  await expect(
    recovery.getByRole("button", { name: "恢复预约结果", exact: true }),
  ).toBeEnabled();
  await recovery
    .getByRole("button", { name: "恢复预约结果", exact: true })
    .click();
  await expect(recovery).toHaveURL(
    new RegExp("/reservation/" + original.id + "$"),
  );
  results.push({ flow: "lost-response-recovered-once", ref: original.id });
  await recovery.close();
  assert.deepEqual(errors, []);
} finally {
  await writeFile(
    out + "/results.json",
    JSON.stringify({ results, errors }, null, 2),
  );
  await browser.close();
}
console.log(JSON.stringify({ results, errors }));
