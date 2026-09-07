import { chromium } from '@playwright/test';
import assert from 'node:assert/strict';
const base = 'http://127.0.0.1:5184';
const browser = await chromium.launch({ headless: true, channel: 'msedge' });
try {
  const context = await browser.newContext({ viewport: { width: 390, height: 844 } });
  await context.addInitScript(() => {
    if (!localStorage.getItem('recovery-fixture-loaded')) {
      localStorage.setItem('puppy-shopping-bag-v2', JSON.stringify([{ key: 'test-recovery-line', product_id: 'starter', quantity: 1, booking: null }]));
      localStorage.setItem('recovery-fixture-loaded', 'true');
    }
  });
  const page = await context.newPage();
  await page.goto(base + '/studio/cart');
  await page.locator('.payable-total').waitFor();
  await page.locator('input[name="name"]').fill('Local Retry QA');
  await page.locator('input[name="contact"]').fill('local-only');
  await page.locator('.consent-label input').check();
  const initialCount = (await (await page.request.get(base + '/studio-api/manage/orders')).json()).total;
  let interrupted = false;
  await page.route('**/studio-api/orders', async route => {
    if (!interrupted) {
      interrupted = true;
      await route.fetch(); // Origin creates the order; client loses the response.
      await route.abort('failed');
    } else await route.continue();
  });
  await page.getByRole('button', { name: '去付款', exact: true }).click();
  await page.getByRole('button', { name: '恢复刚才的结账' }).waitFor();
  await page.reload();
  await page.getByRole('button', { name: '恢复刚才的结账' }).click();
  await page.waitForURL(/\/order\/PS/);
  await page.getByRole('link', { name: '打开虎皮椒收银台' }).waitFor();
  assert.equal(await page.locator('.payment-qr').count(), 0, 'Mobile must not first show QR then switch cashiers');
  const count = (await (await page.request.get(base + '/studio-api/manage/orders')).json()).total;
  assert.equal(count, initialCount + 1, 'Lost-response retry created duplicate orders');
  const id = new URL(page.url()).pathname.split('/').pop();
  await page.request.post(base + '/studio-api/qa/paid/' + id);
  await page.getByRole('button', { name: '刷新付款状态' }).click();
  await page.locator('.order-seal.confirmed').waitFor();
  assert.match(await page.locator('.order-main').innerText(), /安排到店自提/);
  await page.screenshot({ path: '../artifacts/studio-commerce/confirmed-mobile-goods-local-fixture.png', fullPage: true });
  console.log(JSON.stringify({ lostResponseReplay: 'passed', mobileCashier: 'passed', goodsReceipt: 'passed', duplicateOrders: 0 }));
  await context.close();
} finally { await browser.close(); }
