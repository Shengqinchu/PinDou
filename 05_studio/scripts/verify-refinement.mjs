import { chromium, expect } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
import { mkdir, writeFile } from 'node:fs/promises';
import path from 'node:path';

const base = process.env.STUDIO_URL || 'http://127.0.0.1:5184/studio/';
const out = path.resolve('../artifacts/studio-refinement');
await mkdir(out, { recursive: true });
const browser = await chromium.launch({ headless: true, channel: 'msedge' });
const results = [];
try {
  const context = await browser.newContext({ reducedMotion: 'reduce' });
  const page = await context.newPage();
  const pageErrors = [];
  page.on('pageerror', e => pageErrors.push(e.message));
  for (const [width, height] of [[1440, 900], [390, 844], [1080, 665], [320, 740], [2048, 1017]]) {
    await page.setViewportSize({ width, height });
    const routes = [1440, 390].includes(width) ? ['', 'visit', 'shop', 'journal'] : ['', 'visit'];
    for (const route of routes) {
      await page.goto(base + route, { waitUntil: 'networkidle' });
      await page.evaluate(() => document.fonts.ready);
      const overflow = await page.evaluate(() => document.documentElement.scrollWidth > innerWidth + 1);
      const violations = [1440, 390].includes(width) ? (await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21aa']).analyze()).violations.map(v => ({ id: v.id, nodes: v.nodes.map(n => n.target) })) : [];
      await page.screenshot({ path: path.join(out, `${width}-${route || 'home'}.png`) });
      if (!route && [1440, 390].includes(width)) await page.screenshot({ path: path.join(out, `${width}-home-full.png`), fullPage: true });
      results.push({ width, route: route || 'home', overflow, violations });
      expect(overflow, `${width} ${route} overflow`).toBe(false);
      expect(violations, `${width} ${route} accessibility`).toEqual([]);
    }
  }
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto(base, { waitUntil: 'networkidle' });
  await page.evaluate(() => document.fonts.ready);
  const cdp = await context.newCDPSession(page);
  await cdp.send('DOM.enable'); await cdp.send('CSS.enable');
  const { root } = await cdp.send('DOM.getDocument');
  const fonts = {};
  for (const selector of ['.hero h1', '.hero-description']) {
    const { nodeId } = await cdp.send('DOM.querySelector', { nodeId: root.nodeId, selector });
    fonts[selector] = (await cdp.send('CSS.getPlatformFontsForNode', { nodeId })).fonts;
    expect(fonts[selector].some(font => font.isCustomFont && font.familyName.startsWith('PinDou'))).toBe(true);
  }
  await page.getByRole('button', { name: 'Switch to English' }).click();
  await page.screenshot({ path: path.join(out, '1440-home-en.png') });
  expect(await page.locator('.hero h1').evaluate(el => getComputedStyle(el).fontFamily)).toContain('DM Serif Display');
  results.push({ loadedFonts: fonts, englishDisplay: 'DM Serif Display retained', pageErrors });
  expect(pageErrors).toEqual([]);
  await context.close();

  const motionContext = await browser.newContext({ viewport: { width: 1440, height: 900 }, reducedMotion: 'no-preference' });
  const motionPage = await motionContext.newPage();
  await motionPage.goto(base, { waitUntil: 'networkidle' });
  await motionPage.waitForTimeout(1200);
  const button = motionPage.locator('.hero-buttons .button');
  const state = () => button.evaluate(el => { const s=getComputedStyle(el), child=getComputedStyle(el.querySelector('svg'));return { transform:s.transform, duration:s.transitionDuration, ease:s.transitionTimingFunction, childDuration:child.transitionDuration, childEase:child.transitionTimingFunction, childTransform:child.transform, shadow:s.boxShadow }; });
  const idle = await state(); await button.hover(); await motionPage.waitForTimeout(350); const hover = await state();
  await motionPage.mouse.down(); await motionPage.waitForTimeout(350); const pressed = await state();
  // Move away before release so this remains a visual check, not navigation.
  await motionPage.mouse.move(10, 10); await motionPage.mouse.up(); await motionPage.waitForTimeout(350); const released = await state();
  expect(hover.transform).not.toBe(idle.transform);
  expect(pressed.transform).not.toBe(hover.transform);
  expect(released.transform).toBe(idle.transform);
  expect(new Set(hover.duration.split(',').map(v=>v.trim()))).toEqual(new Set(['0.3s']));
  expect(new Set(hover.childDuration.split(',').map(v=>v.trim()))).toEqual(new Set(['0.3s']));
  await motionPage.emulateMedia({ reducedMotion: 'reduce' }); await button.hover();
  const reduced = await state();expect(reduced.transform).toBe('none');expect(reduced.childTransform).toBe('none');
  results.push({ buttonStates: { idle, hover, pressed, released, reduced } });
  await motionContext.close();

  const dateContext = await browser.newContext({ timezoneId: 'Asia/Tokyo' });
  const datePage = await dateContext.newPage();
  // A visitor in another timezone still selects Hamilton local dates/times.
  await datePage.clock.install({ time: new Date('2026-09-08T23:10:00Z') });
  await datePage.goto(base + 'visit');
  await datePage.locator('input[name=date]').fill('2026-09-08');
  expect(await datePage.locator('select[name=start]').inputValue()).toBe('19:30');
  await datePage.locator('select[name=start]').selectOption('22:30');
  await expect(datePage.locator('select[name=end]')).toHaveValue('23:00');
  await datePage.locator('input[value=pair]').check();await expect(datePage.locator('input[name=guests]')).toHaveValue('2');
  await datePage.locator('input[value=day]').check();await expect(datePage.locator('input[name=guests]')).toHaveValue('1');
  await datePage.clock.setSystemTime(new Date('2026-09-09T03:10:00Z'));await datePage.clock.runFor(31000);
  await expect(datePage.getByRole('button', { name: '提交预约意向', exact: true })).toBeDisabled();
  await expect(datePage.locator('input[name=date]')).toBeEnabled();
  await datePage.locator('input[name=date]').fill('2026-09-09');
  await expect(datePage.getByRole('button', { name: '提交预约意向', exact: true })).toBeEnabled();
  results.push({ dates: 'Hamilton timezone, expired starts removed, end repaired, plan guest counts, recovery to next day passed' });
  await dateContext.close();
} finally {
  await writeFile(path.join(out, 'verification.json'), JSON.stringify(results, null, 2));
  await browser.close();
}
console.log(JSON.stringify(results, null, 2));
