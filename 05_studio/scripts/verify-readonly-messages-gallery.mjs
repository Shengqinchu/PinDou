// Read-only browser check with public catalog data and disposable message responses.
import { chromium, expect } from '@playwright/test';
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import { fileURLToPath } from 'node:url';

const base = process.argv[2] || 'http://127.0.0.1:4184';
const publicBase = 'https://pindoupuppy.com';
const mode = base === publicBase ? 'live' : 'local';
const out = fileURLToPath(new URL('../../artifacts/messages-gallery-20260924/', import.meta.url));
await fs.mkdir(out, { recursive: true });
const browser = await chromium.launch({ channel: 'msedge', headless: true });
const results = [];
try {
  const catalog = await browser.newContext().then(async context => {
    try {
      const response = await context.request.get(publicBase + '/studio-api/shop/catalog');
      assert(response.ok(), `Public catalog: ${response.status()}`);
      return response.json();
    }
    finally { await context.close(); }
  });
  const cat = catalog.products.find(product => product.zh === '小猫摇摇乐');
  assert(cat?.images.length > 1, 'The production cat product needs multiple photos');

  for (const viewport of [{ width: 1440, height: 900 }, { width: 390, height: 844 }]) {
    const context = await browser.newContext({ viewport, reducedMotion: 'reduce' });
    await context.addInitScript(() => {
      localStorage.setItem('pd_web_token', 'local-gallery-qa');
      localStorage.setItem('puppy-studio-locale', 'zh');
    });
    const page = await context.newPage();
    const errors = [];
    page.on('pageerror', error => errors.push(error.message));
    await page.route('**/studio-api/**', async route => {
      const path = new URL(route.request().url()).pathname;
      if (path === '/studio-api/shop/catalog') return route.fulfill({ json: { ...catalog, products: [cat] } });
      if (path.startsWith('/studio-api/media/') || path.startsWith('/studio-api/previews/')) {
        return mode === 'live' ? route.continue() : route.fulfill({ response: await route.fetch({ url: publicBase + path }) });
      }
      if (path === '/studio-api/auth/me') return route.fulfill({ json: { user: { id: 'local-gallery-qa', email: '', nickname: 'QA' } } });
      if (path === '/studio-api/auth/messages') return route.fulfill({ json: { items: [{ id: 'local-message', seq: 1, sender_role: 'system', body: 'Booking confirmed', created_at: 1780000000 }], has_older: false } });
      if (path === '/studio-api/auth/messages/read') return route.fulfill({ json: { ok: true } });
      return route.fulfill({ status: 404, json: {} });
    });

    await page.goto(base + '/messages');
    await expect(page.getByRole('heading', { name: '我的消息' })).toBeVisible();
    await expect(page.locator('.site-conversation-body')).toContainText('Booking confirmed');
    await expect(page.locator('.site-chat-composer')).toHaveCount(0);
    await page.screenshot({ path: `${out}/${mode}-messages-${viewport.width}.png` });

    await page.goto(base + '/shop?section=finished');
    await page.locator('.shop-card').filter({ hasText: '小猫摇摇乐' }).locator('.shop-card-preview').click();
    const dialog = page.locator('dialog[data-phase="open"]');
    await dialog.waitFor();
    const thumbs = dialog.locator('.shop-thumbnails');
    await expect(thumbs.locator('button')).toHaveCount(cat.images.length);
    assert(await thumbs.evaluate(element => element.scrollWidth <= element.clientWidth + 1), 'Thumbnail row must not scroll horizontally');
    const image = dialog.locator('.shop-detail-image');
    await image.evaluate(element => element.decode());
    await dialog.locator('.shop-image-nav.next').click();
    await expect(thumbs.locator('button').nth(1)).toHaveAttribute('aria-pressed', 'true');
    await expect(image).toHaveAttribute('src', cat.images[1]);
    await dialog.locator('.shop-image-nav.previous').click();
    await expect(image).toHaveAttribute('src', cat.images[0]);
    await thumbs.locator('button').last().click();
    await expect(image).toHaveAttribute('src', cat.images.at(-1));
    await image.scrollIntoViewIfNeeded();
    const bounds = await image.boundingBox();
    assert(bounds);
    await page.mouse.click(bounds.x + bounds.width - 15, bounds.y + bounds.height / 2);
    await expect(image).toHaveAttribute('src', cat.images[0]);
    await image.evaluate(element => element.decode());
    await page.screenshot({ path: `${out}/${mode}-gallery-${viewport.width}.png` });
    assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1));
    assert.deepEqual(errors, []);
    results.push({ viewport, messageReadOnly: true, photos: cat.images.length, thumbnailsWrapped: true, sideNavigation: true });
    await context.close();
  }
  await fs.writeFile(`${out}/${mode}-results.json`, JSON.stringify(results, null, 2));
  console.log(JSON.stringify(results));
} finally {
  await browser.close();
}
