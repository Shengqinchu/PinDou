import { chromium, expect } from '@playwright/test';

const browser = await chromium.launch({ headless: true, channel: 'msedge' });
try {
  const page = await browser.newPage();
  await page.goto('http://127.0.0.1:5184/studio/shop');
  await page.getByRole('button', { name: '将刚好缺的那一抹颜色加入清单', exact: true }).click();
  await page.getByLabel('你的称呼', { exact: true }).fill('Submit guard QA');
  await page.getByLabel('微信号', { exact: true }).fill('local-only-qa');
  await page.getByRole('checkbox').check();
  const keys = [];
  await page.route('**/studio-api/requests', async route => {
    keys.push(route.request().headers()['idempotency-key']);
    if (keys.length === 1) {
      await new Promise(resolve => setTimeout(resolve, 1200));
      await route.fulfill({ status: 503, contentType: 'application/json', body: '{}' });
    } else await route.continue();
  });
  await page.getByRole('button', { name: '提交自提询单', exact: true }).click();
  await expect(page.getByRole('button', { name: '增加刚好缺的那一抹颜色的数量', exact: true })).toBeDisabled();
  await expect(page.getByRole('button', { name: '减少刚好缺的那一抹颜色的数量', exact: true })).toBeDisabled();
  await expect(page.getByRole('button', { name: '将刚好缺的那一抹颜色加入清单', exact: true })).toBeDisabled();
  await expect(page.getByRole('alert')).toBeVisible();
  await expect(page.getByLabel('你的称呼', { exact: true })).toHaveValue('Submit guard QA');
  await expect(page.getByRole('button', { name: '增加刚好缺的那一抹颜色的数量', exact: true })).toBeEnabled();
  await page.getByRole('button', { name: '提交自提询单', exact: true }).click();
  await expect(page.getByText(/PUP-[A-F0-9]{12}/)).toBeVisible();
  expect(keys).toHaveLength(2);
  expect(keys[1]).toBe(keys[0]);
  console.log('PASS: cart locked during submission; failure preserves input; retry reuses key and saves successfully.');
} finally { await browser.close(); }
