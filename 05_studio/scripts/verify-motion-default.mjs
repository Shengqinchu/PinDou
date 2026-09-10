// First visits must be tested with empty storage and native media preferences.
// No login, email, generation or reservation submissions are made by this test.
import { chromium, firefox, webkit, expect } from '@playwright/test';
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';

const base = process.env.PINDOU_QA_BASE || 'http://127.0.0.1:19684';
const out = new URL(process.env.PINDOU_QA_OUTPUT || '../../artifacts/studio-motion-default/', import.meta.url);
await fs.mkdir(out, { recursive: true });
const checks = [], errors = [], mutations = [];
const key = 'puppy-studio-motion';
const y = element => element.evaluate(e => new DOMMatrix(getComputedStyle(e).transform).m42);
async function setup(context) {
  await context.addInitScript(() => {
    window.__motionSamples = [];
    let started = 0;
    const deadline = performance.now() + 15000;
    const sample = now => {
      const line = document.querySelector('.vision-title > .lift-line');
      if (line) {
        started ||= now;
        window.__motionSamples.push({ time: now - started, opacity: +getComputedStyle(line).opacity, motion: document.documentElement.dataset.motion });
      }
      if (now < deadline && (!started || now - started < 2000)) requestAnimationFrame(sample);
    };
    requestAnimationFrame(sample);
  });
  const page = await context.newPage();
  page.on('pageerror', e => errors.push(e.message));
  page.on('request', r => { if (!['GET', 'HEAD', 'OPTIONS'].includes(r.method())) mutations.push({method:r.method(),url:r.url()}); });
  page.setDefaultTimeout(10000);
  return page;
}
async function home(page, suffix = '/') {
  await page.goto(base + suffix);
  await expect(page.locator('.vision-title .lift-hit').first()).toBeVisible();
  await expect.poll(() => page.locator('.vision-title > .lift-line').first().evaluate(e => getComputedStyle(e).opacity)).toBe('1');
  await page.waitForTimeout(650);
}
async function lifted(page) {
  const hit = page.locator('.vision-title .lift-hit').first(), glyph = hit.locator('.lift-glyph');
  await hit.hover();
  await expect.poll(() => y(glyph), {intervals:[50,100]}).toBeLessThan(-1);
  await page.waitForTimeout(800);
  const held = await y(glyph);
  assert(held < -1, 'A stationary pointer must keep its letter raised');
  assert.equal(await y(page.locator('.vision-title .lift-glyph').nth(4)), 0, 'Adjacent letters should remain independent');
  await page.mouse.move(8,180);
  await expect.poll(() => y(glyph)).toBe(0);
  return held;
}
for (const [engineName, engine] of [['chromium',chromium],['firefox',firefox],['webkit',webkit]]) {
  const browser = await engine.launch({headless:true});
  try {
    for (const native of [null, 'reduce', 'no-preference']) {
      const context = await browser.newContext({viewport:{width:1440,height:1000},reducedMotion:native});
      const page = await setup(context);
      await home(page);
      await expect(page.locator('html')).toHaveAttribute('data-motion','full');
      const samples = await page.evaluate(() => window.__motionSamples);
      assert(samples.some(s => s.opacity > 0 && s.opacity < .98), 'First visit skipped its entrance');
      assert(samples.every(s => s.motion === 'full'), 'Initial frames used a different motion mode');
      assert.equal(await page.evaluate(k => localStorage.getItem(k), key), null, 'Default must not masquerade as a visitor choice');
      const held = await lifted(page);
      const puppy = page.locator('.hero-puppy'), touch = puppy.locator('.motif-touch');
      await puppy.click();await page.waitForTimeout(90);
      const scale = await touch.evaluate(e => new DOMMatrix(getComputedStyle(e).transform).m22);
      assert(scale < .99, 'Dog click must visibly squish on a fresh visit');
      const drift = await puppy.locator('.motif-float').evaluate(e => getComputedStyle(e).transform);
      await page.waitForTimeout(240);
      assert.notEqual(await puppy.locator('.motif-float').evaluate(e => getComputedStyle(e).transform),drift);
      checks.push({case:'fresh-private-context',engine:engineName,native,system:await page.locator('html').getAttribute('data-system-motion'),held,scale,entrance:true});
      if (native === null) {
        // Changing the OS while on the default must not disable or restart motion.
        await page.emulateMedia({reducedMotion:'reduce'});
        await expect(page.locator('html')).toHaveAttribute('data-motion','full');
        await page.reload();await expect(page.locator('html')).toHaveAttribute('data-motion','full');
        await page.goto(base + '/visit?step=1');
        const plan = page.locator('.visit-plans > label').first();await plan.hover();
        await expect.poll(() => y(plan)).toBeLessThan(-1);
        await page.goto(base + '/tools');
        const mode = page.locator('.mode-card').first();await mode.hover();
        await expect.poll(() => y(mode)).toBeLessThan(-.5);
        checks.push({case:'native-reload-visit-generator',engine:engineName});
      }
      await context.close();
    }
    // A coarse pointer still gets entry and tap motion, without requiring hover.
    if(engineName !== 'firefox') {
      const context = await browser.newContext({viewport:{width:390,height:844},isMobile:true,hasTouch:true,reducedMotion:'reduce'});
      const page = await setup(context);await home(page);
      await expect(page.locator('html')).toHaveAttribute('data-motion','full');
      const puppy=page.locator('.hero-puppy');await puppy.tap();await page.waitForTimeout(90);
      assert(await puppy.locator('.motif-touch').evaluate(e=>new DOMMatrix(getComputedStyle(e).transform).m22)<.99);
      assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));
      checks.push({case:'touch-first-visit',engine:engineName});await context.close();
    }
    if(engineName !== 'chromium') continue;
    for(const stored of ['reduced','system']) {
      const context=await browser.newContext({reducedMotion:'reduce'});const page=await setup(context);
      await home(page,'/?motion='+stored);
      await expect(page.locator('html')).toHaveAttribute('data-motion','reduced');
      assert.equal(await page.evaluate(k=>localStorage.getItem(k),key),stored);
      await page.goto(base+'/');await page.reload();
      await expect(page.locator('html')).toHaveAttribute('data-motion','reduced');
      const glyph=page.locator('.vision-title .lift-glyph').first();await page.locator('.vision-title .lift-hit').first().hover();assert.equal(await y(glyph),0);
      await page.emulateMedia({reducedMotion:'no-preference'});
      await expect(page.locator('html')).toHaveAttribute('data-motion',stored==='system'?'full':'reduced');
      checks.push({case:'explicit-choice-persists',choice:stored});await context.close();
    }
    for(const storageCase of ['blocked','invalid']) {
      const context=await browser.newContext({reducedMotion:'reduce'});
      await context.addInitScript(({storageCase,key})=>{
        if(storageCase==='blocked')Object.defineProperty(window,'localStorage',{get(){throw new DOMException('Storage blocked','SecurityError');}});
        else localStorage.setItem(key,'unexpected-old-value');
      },{storageCase,key});
      const page=await setup(context);await home(page);await expect(page.locator('html')).toHaveAttribute('data-motion','full');await lifted(page);
      await home(page,'/?motion=reduced');await expect(page.locator('html')).toHaveAttribute('data-motion','reduced');
      checks.push({case:'storage-fallback-and-explicit-override',storageCase});await context.close();
    }
    const context=await browser.newContext({reducedMotion:'reduce'}),page=await setup(context);await home(page);
    const other=await setup(context);await home(other,'/?motion=reduced');
    await expect(page.locator('html')).toHaveAttribute('data-motion','reduced');
    await home(other,'/?motion=full');await expect(page.locator('html')).toHaveAttribute('data-motion','full');
    await home(other,'/?motion=system');await expect(page.locator('html')).toHaveAttribute('data-motion','reduced');
    await other.evaluate(k=>localStorage.removeItem(k),key);await expect(page.locator('html')).toHaveAttribute('data-motion','full');
    await other.goto(base+'/');await other.reload();await expect(other.locator('html')).toHaveAttribute('data-motion','full');
    checks.push({case:'cross-tab-explicit-system-and-clear'});await context.close();
  } finally {await browser.close();}
}
await fs.writeFile(new URL('verification.json',out),JSON.stringify({checks,errors,mutations},null,2));
assert.deepEqual(errors,[]);assert.deepEqual(mutations,[]);
console.log(JSON.stringify({checks,errors,mutations},null,2));
