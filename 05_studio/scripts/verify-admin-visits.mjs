// Real local service + disposable accounts; isolated from the owner's WeChat and production.
import { chromium, webkit, expect } from '@playwright/test';
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import copy from '../src/content/admin-visits.json' with { type: 'json' };
import wallet from '../src/content/wallet.json' with { type: 'json' };
import reservation from '../src/content/components-admin-ReservationsPanel.json' with { type: 'json' };

const apiOrigin = 'http://127.0.0.1:8127', site = 'http://127.0.0.1:5287';
const out = new URL('../../artifacts/admin-visits/', import.meta.url);
await fs.mkdir(out, { recursive: true });
const results = [];
const plus = (day, n) => { const date = new Date(day+'T12:00:00Z'); date.setUTCDate(date.getUTCDate()+n); return date.toISOString().slice(0,10); };
for (const [engine, type] of [['chromium', chromium], ['webkit', webkit]]) {
  const browser = await type.launch({ headless: true });
  try {
    for (const lang of ['zh', 'en']) {
      const word = key => copy[key][lang === 'zh' ? 0 : 1], w = key => wallet[key][lang === 'zh' ? 0 : 1], r = key => reservation[key][lang === 'zh' ? 0 : 1];
      const owner = `qa-email-adminvisits-${engine}-${lang}-${Date.now()}`;
      const context = await browser.newContext({ viewport: { width: 1440, height: 1000 }, reducedMotion: 'reduce' });
      const api = async (path, method='GET', data, admin=true) => {
        const response = await context.request.fetch(apiOrigin+path, { method, data, headers: { Authorization: `Bearer ${admin ? 'local-admin-visits' : owner}` } });
        assert(response.ok(), `${path}: ${response.status()} ${await response.text()}`); return response.json();
      };
      await api('/studio-api/auth/me', 'GET', undefined, false);
      const baseline = await api('/studio-api/auth/wallet', 'GET', undefined, false);
      const calendar = await api('/studio-api/reservation-calendar');
      const tomorrow = calendar.days.find(day => day.date > calendar.today && !day.closed);
      const yesterday = plus(calendar.today, -1);
      await context.addInitScript(({ lang, owner }) => {
        localStorage.setItem('pd_web_token', owner); localStorage.setItem('pd_token', owner);
        localStorage.setItem('puppy-studio-language', lang);
        sessionStorage.setItem('puppy-studio-admin', 'local-admin-visits');
      }, { lang, owner });
      let loseNext = false, lostRecord = '', forceRejected = false;
      const submissions = [];
      await context.route('**/studio-api/**', async route => {
        const req = route.request(), url = new URL(req.url()), headers = {};
        for (const key of ['authorization', 'content-type', 'idempotency-key']) if (req.headers()[key]) headers[key] = req.headers()[key];
        const creation = req.method() === 'POST' && url.pathname.endsWith(`/members/${owner}/reservations`);
        if (creation) submissions.push({ key: headers['idempotency-key'], body: req.postData() });
        if (creation && forceRejected) { forceRejected = false; await route.fulfill({ status: 409, json: { detail: 'reservation_interval_unavailable' } }); return; }
        const response = await context.request.fetch(apiOrigin+url.pathname+url.search, { method: req.method(), headers, data: req.postDataBuffer() || undefined });
        if (creation && loseNext) { loseNext = false; assert.equal(response.status(), 201); lostRecord = (await response.json()).id; await route.abort('failed'); return; }
        await route.fulfill({ response });
      });
      await context.route('**/api/v1/**', route => route.fulfill({ json: {} }));
      const page = await context.newPage(), errors = [];
      page.on('pageerror', error => errors.push(error.message));
      page.setDefaultTimeout(15000);
      const memberURL = `${site}/manage?view=members&member=${owner}`;
      const pane = page.locator('dialog[open] .member-visits'), form = pane.locator('form');
      try {
        await page.goto(memberURL);
        await expect(pane).toBeVisible();
        await expect(pane).toContainText(word('no_reward'));
        await pane.getByRole('button', { name: word('add_booking'), exact: true }).click();
        await form.getByLabel(word('date'), { exact: true }).fill(tomorrow.date);
        await form.getByRole('combobox', { name: word('start'), exact: true }).selectOption('10:00');
        await form.getByRole('combobox', { name: word('end'), exact: true }).selectOption('12:00');
        await form.getByLabel(word('reason'), { exact: true }).fill('Local host request');
        await expect(form.getByRole('button', { name: word('save_booking'), exact: true })).toBeEnabled();
        await page.keyboard.press('Escape'); await expect(page.locator('dialog[open]')).toHaveCount(0);
        await page.locator('.desk-language').click();
        await page.locator('.member-row').filter({ hasText: baseline.account.customer_code }).click();
        await expect(form.getByLabel(copy.reason[lang === 'zh' ? 1 : 0], { exact: true })).toHaveValue('Local host request');
        await page.keyboard.press('Escape'); await expect(page.locator('dialog[open]')).toHaveCount(0);
        await page.locator('.desk-language').click();
        await page.locator('.member-row').filter({ hasText: baseline.account.customer_code }).click();
        await expect(form.getByLabel(word('reason'), { exact: true })).toHaveValue('Local host request');
        forceRejected = true;
        await form.getByRole('button', { name: word('save_booking'), exact: true }).click();
        await expect(form.getByLabel(word('reason'), { exact: true })).toBeEnabled();
        await expect(pane.locator('.desk-error').first()).toBeVisible();
        await form.getByRole('button', { name: word('save_booking'), exact: true }).click();
        await expect(pane.locator('.wallet-saved')).toHaveText(word('saved'));
        let all = await api('/studio-api/manage/reservations?owner_id='+owner);
        assert.equal(all.total, 1); assert.equal(all.items[0].creation_source, 'admin_booking');
        const bookingId = all.items[0].id;
        await pane.getByRole('button', { name: word('add_backfill'), exact: true }).click();
        await form.getByLabel(word('date'), { exact: true }).fill(yesterday);
        await form.getByLabel(w('actual_hours'), { exact: true }).fill('0.5');
        await form.getByLabel(w('actual_guests'), { exact: true }).fill('2');
        await form.getByLabel(word('reason'), { exact: true }).fill('Past visit checked with host');
        await form.getByLabel(w('public_note'), { exact: true }).fill('Visible actual visit');
        await form.getByLabel(w('private_note'), { exact: true }).fill('Host-only note');
        for (const [width, height] of [[1440,1000],[390,844],[320,568],[844,390]]) {
          await page.setViewportSize({ width, height });
          await expect(form).toBeVisible();
          const dimensions = await page.locator('dialog[open] .drawer-panel').evaluate(el => ({ width: el.clientWidth, scroll: el.scrollWidth }));
          assert(dimensions.scroll <= dimensions.width+1, `${engine} ${lang} ${width}: drawer overflow`);
          for (const field of await form.locator('input,select,textarea').all()) {
            const box = await field.boundingBox(); assert(box && box.width > 40 && box.x >= 0 && box.x+box.width <= width+1);
          }
          await form.getByLabel(w('actual_hours'), { exact: true }).scrollIntoViewIfNeeded();
          await page.screenshot({ path: fileURLToPath(new URL(`${engine}-${lang}-${width}.png`, out)) });
          results.push({ engine, lang, width, height, layout: 'pass' });
        }
        await page.setViewportSize({ width:390, height:844 });
        loseNext = true;
        await form.getByRole('button', { name: word('save_backfill'), exact: true }).click();
        await expect(pane.locator('.wallet-uncertain')).toContainText(word('uncertain'));
        assert(lostRecord);
        const attempted = submissions.at(-1);
        await page.reload();
        await expect(pane.locator('.wallet-uncertain')).toBeVisible();
        await expect(form.getByLabel(word('reason'), { exact:true })).toBeDisabled();
        await pane.locator('.wallet-uncertain').getByRole('button', { name: w('retry'), exact: true }).click();
        await expect(pane.locator('.wallet-saved')).toHaveText(word('saved'));
        assert.deepEqual(submissions.at(-1), attempted);
        all = await api('/studio-api/manage/reservations?owner_id='+owner);
        assert.equal(all.total, 2);
        const backfill = all.items.find(item => item.id === lostRecord);
        assert.equal(backfill.actual_minutes, 30); assert.equal(backfill.actual_guests, 2); assert.equal(backfill.booking.guests, 2);
        await pane.locator('.member-visit-row').filter({ hasText: word('admin_backfill') }).getByRole('link', { name: word('open_record'), exact: true }).click();
        const dialog = page.locator('dialog[open]');
        await expect(dialog).toContainText(word('admin_backfill'));
        await expect(dialog).toContainText(word('no_reward'));
        await dialog.locator('.reservation-history summary').click();
        await expect(dialog.locator('.reservation-history')).toContainText('Past visit checked with host');
        await dialog.getByLabel(w('actual_hours'), { exact: true }).fill('1.5');
        await dialog.getByRole('button', { name: r('save_arrangement_87aa75'), exact: true }).click();
        await expect(page.locator('dialog[open]')).toHaveCount(0);
        const updated = (await api('/studio-api/manage/reservations?owner_id='+owner)).items.find(item => item.id === lostRecord);
        assert.equal(updated.actual_minutes, 90); assert.equal(updated.creation_source, 'admin_backfill');
        const finalWallet = await api('/studio-api/auth/wallet', 'GET', undefined, false);
        assert.equal(finalWallet.account.points, baseline.account.points);
        assert.equal(finalWallet.account.minutes, baseline.account.minutes);
        const cash = await api('/studio-api/manage/finance');
        assert.equal(cash.items.filter(item => item.reservation_id === lostRecord).length, 1);
        await page.goto(`${site}/reservation/${lostRecord}`);
        await expect(page.locator('body')).toContainText('Visible actual visit');
        assert(!(await page.locator('body').innerText()).includes('Host-only note'));
        assert.deepEqual(errors, []);
        results.push({ engine, lang, bookingId, pastVisitId: lostRecord, booking: 'pass', backfill: 'pass', reloadRetry: 'same key and body', edit: 'pass', points: finalWallet.account.points, financeEntries: 1, guestReceipt: 'pass' });
        console.log(`${engine} ${lang}: creation, drafts, rejected save, lost response/reload, edit, ledger, finance and guest receipt passed`);
      } catch (error) {
        await page.screenshot({ path: fileURLToPath(new URL(`FAILED-${engine}-${lang}.png`, out)) });
        await fs.writeFile(new URL(`FAILED-${engine}-${lang}.txt`, out), await page.locator('body').ariaSnapshot());
        throw error;
      } finally { await context.close(); }
    }
  } finally { await browser.close(); }
}
await fs.writeFile(new URL('results.json', out), JSON.stringify(results, null, 2)+'\n');
