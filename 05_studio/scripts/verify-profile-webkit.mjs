import {webkit,expect} from '@playwright/test';
import fs from 'node:fs/promises';
import assert from 'node:assert/strict';
const browser=await webkit.launch({headless:true});
try{
 const context=await browser.newContext({locale:'en-CA',viewport:{width:375,height:812},isMobile:true,hasTouch:true});
 const page=await context.newPage(),errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.goto('http://127.0.0.1:19676/account');
 await page.getByRole('button',{name:'Password',exact:true}).click();
 await page.getByLabel('Email address',{exact:true}).fill(`webkit-${Date.now()}@example.test`);
 await page.getByLabel('Password',{exact:true}).fill('local-password');
 await page.locator('.account-form').getByRole('button',{name:'Sign in',exact:true}).click();
 await page.getByRole('button',{name:'About your points',exact:true}).tap();await expect(page.getByRole('tooltip')).toContainText('100 points = CAD 1');
 await page.locator('h1').tap();await expect(page.getByRole('tooltip')).toHaveCount(0);
 await page.getByRole('button',{name:'Edit profile',exact:true}).tap();
 const dialog=page.locator('dialog[open]').last();await expect(dialog).toHaveAttribute('data-phase','open');
 await dialog.locator('.profile-field-label .info-tip-trigger').tap();
 await expect(dialog.getByRole('tooltip')).toContainText('1–20 characters');
 assert(await dialog.evaluate(el=>el.scrollWidth<=el.clientWidth+1));
 await dialog.getByRole('button',{name:'Cancel',exact:true}).tap();await expect(dialog).toHaveCount(0);
 assert.deepEqual(errors,[]);
 await fs.writeFile(new URL('../../artifacts/account-refinement/webkit.json',import.meta.url),JSON.stringify({passed:true,engine:'webkit',width:375,checks:['email login','touch hints','modal hint top layer','no overflow','cancel focus'],errors},null,2));
 console.log('WebKit mobile: login, touch hints, editor top layer, cancel and layout passed');await context.close();
}finally{await browser.close();}
