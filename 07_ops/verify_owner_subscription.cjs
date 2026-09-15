// Disposable transport tests. These do not grant WeChat permissions or send messages.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const root = path.resolve(__dirname, '..');
const ts = require('../05_frontend/node_modules/typescript');
const vue = require('../05_frontend/node_modules/vue');
const compiler = require('../05_frontend/node_modules/@vue/compiler-sfc');
const tested = [];
function compile(source, stubs, extra = {}) {
  const module = {exports: {}};
  const code = ts.transpileModule(source, {compilerOptions: {module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020, esModuleInterop: true}}).outputText;
  vm.runInNewContext(code, {module, exports: module.exports, require: id => {
    if (id in stubs) return stubs[id];
    if (id.endsWith('.json')) return JSON.parse(fs.readFileSync(path.resolve(root, '05_frontend/src/pages/studio', id), 'utf8'));
    throw Error('Unexpected dependency: ' + id);
  }, console, Date, ...extra});
  return module.exports;
}
function helper({native = true, status = {}, seconds = 300, failures = 0, throws = false} = {}) {
  const calls = [], requests = [];
  const source = fs.readFileSync(path.join(root, '05_frontend/src/utils/owner-subscription.ts'), 'utf8')
    .replace(new RegExp('// #' + (native ? 'ifndef' : 'ifdef') + ' MP-WEIXIN[\\s\\S]*?// #endif', 'g'), '')
    .replace(/\/\/ #(ifn?def MP-WEIXIN|endif)/g, '');
  const api = compile(source, {'./miniapp-client': {
    miniSession: async () => ({ticket: 'owner-a-proof', expires_in: seconds}),
    studioCall: async (...args) => {calls.push(args); if (args[0].endsWith('/status')) return {bound: true, admin: true, enabled: true, template_id: 'template-a', nonce: 'nonce-a', ...status}; if (failures-- > 0) throw Error('Interrupted acknowledgement'); return {};},
  }}, {uni: {requestSubscribeMessage: options => {requests.push(options); if (throws) throw Error('Unavailable API');}}});
  return {api, calls, requests};
}
async function test(name, fn) {await fn(); tested.push(name);}
function page() {
  const calls = [], requests = [], hooks = {}, source = fs.readFileSync(path.join(root, '05_frontend/src/pages/studio/manage-reservation.vue'), 'utf8');
  const script = compiler.compileScript(compiler.parse(source).descriptor, {id: 'owner-save-qa'}).content;
  const prompt = {ticket: 'p', template: 't', nonce: 'n', expires: Date.now() + 60000, used: false};
  const admin = {adminCall: async (...args) => {calls.push(args); if (args[0] === '/manage/reservations') return {items: [{id: 'VIS-TEST', status: 'confirmed', version: 2, booking: {guests: 1}, payload: {}}]}; return {};}, adminError: () => 'Save failed', confirmAdmin: async () => true, goAdmin() {}};
  const native = {prepareOwnerSubscription: async () => prompt, ownerSubscriptionReady: p => !!p && !p.used && p.expires > Date.now(), requestOwnerSubscription: (p, action) => {requests.push({p, action}); p.used = true; return action.then(() => 'accept');}};
  const stubs = {'vue': vue, '@dcloudio/uni-app': {onLoad: f => hooks.load = f, onShow: f => hooks.show = f, onUnload: f => hooks.unload = f},
    '../../utils/studio-native': {useStudioNative: () => ({say: words => words[0]})}, '../../utils/studio-admin': admin, '../../utils/owner-subscription': native,
    '../../../../05_studio/src/time-units': {hoursInput: n => n == null ? '' : String(n/60), minutesFromHours: n => n.trim() ? Number(n)*60 : null},
    '../../components/StudioAdminShell.vue': {}, '../../components/StudioCustomerIdentity.vue': {}, '../../components/StudioOwnerSaveConfirm.vue': {}};
  const result = compile(script, stubs, {uni: {showToast() {}}}).default.setup({}, {expose() {}});
  hooks.load({id: 'VIS-TEST'});
  result.entry.value = {id: 'VIS-TEST', status: 'pending', version: 1};
  result.draft.status = 'confirmed';
  result.alertPrompt.value = prompt;
  return {result, calls, requests, hooks};
}
(async () => {
  await test('prepare does not request permission; tap calls WeChat synchronously', async () => {
    const h = helper(), prompt = await h.api.prepareOwnerSubscription(); assert.equal(h.requests.length, 0);
    const result = h.api.requestOwnerSubscription(prompt); assert.equal(h.requests.length, 1);
    h.requests[0].success({'template-a': 'accept'}); assert.equal(await result, 'accept');
    const call = h.calls.find(c => c[0].endsWith('/subscribe')); assert.equal(call[2], 'owner-a-proof'); assert.equal(call[1].nonce, 'nonce-a');
    assert.equal(await h.api.requestOwnerSubscription(prompt), 'unavailable'); assert.equal(h.requests.length, 1);
  });
  for (const status of [{bound: false}, {admin: false}, {enabled: false}, {template_id: ''}, {nonce: ''}]) {
    await test('unavailable identity/config ' + Object.keys(status)[0], async () => {const h = helper({status}); assert.equal(await h.api.prepareOwnerSubscription(), null); assert.equal(h.requests.length, 0);});
  }
  await test('expired proof never requests a permission', async () => {const h = helper({seconds: 20}); assert.equal(await h.api.prepareOwnerSubscription(), null); const p = {expires: Date.now()-1, used: false}; assert.equal(await h.api.requestOwnerSubscription(p), 'unavailable'); assert.equal(h.requests.length, 0);});
  for (const choice of ['reject', 'ban']) await test(choice + ' is recorded without an accept', async () => {
    const h = helper(), p = await h.api.prepareOwnerSubscription(), result = h.api.requestOwnerSubscription(p);
    h.requests[0].success({'template-a': choice}); assert.equal(await result, choice); assert.equal(h.calls.at(-1)[1].result, choice);
  });
  await test('booking save finishes before a grant wakes a pending notice', async () => {
    const h = helper(), p = await h.api.prepareOwnerSubscription(); let finish;
    const action = new Promise(r => finish = r), result = h.api.requestOwnerSubscription(p, action);
    h.requests[0].success({'template-a': 'accept'}); await Promise.resolve(); assert.equal(h.calls.length, 1);
    finish(); assert.equal(await result, 'accept'); assert.equal(h.calls.length, 2);
  });
  await test('duplicate callbacks cannot record another grant', async () => {
    const h = helper(), p = await h.api.prepareOwnerSubscription(), result = h.api.requestOwnerSubscription(p);
    h.requests[0].success({'template-a': 'accept'}); h.requests[0].success({'template-a': 'accept'}); h.requests[0].fail(); assert.equal(await result, 'accept'); assert.equal(h.calls.length, 2);
  });
  await test('interrupted acknowledgement retries only the same nonce', async () => {
    const h = helper({failures: 1}), p = await h.api.prepareOwnerSubscription(), result = h.api.requestOwnerSubscription(p);
    h.requests[0].success({'template-a': 'accept'}); assert.equal(await result, 'accept'); assert.equal(h.calls.length, 3); assert.equal(JSON.stringify(h.calls[1]), JSON.stringify(h.calls[2]));
  });
  await test('unrecorded permission never reports success', async () => {
    const h = helper({failures: 2}), p = await h.api.prepareOwnerSubscription(), result = h.api.requestOwnerSubscription(p);
    h.requests[0].success({'template-a': 'accept'}); assert.equal(await result, 'failed');
  });
  await test('permission API failure does not throw', async () => {const h = helper({throws: true}); assert.equal(await h.api.requestOwnerSubscription(await h.api.prepareOwnerSubscription()), 'failed');});
  await test('H5 does not use native session or permission APIs', async () => {const h = helper({native: false}); assert.equal(await h.api.prepareOwnerSubscription(), null); assert.equal(h.calls.length, 0); assert.equal(h.requests.length, 0);});
  await test('visible confirmation precedes both mutation and permission', async () => {const p = page(); await p.result.save(); assert(p.result.savePrompt.value); assert.equal(p.calls.length, 0); assert.equal(p.requests.length, 0); p.result.dismissSave(); assert.equal(p.calls.length, 0);});
  await test('unchecked alert saves the booking without subscription', async () => {const p = page(); await p.result.save(); p.result.confirmSave(false); await new Promise(r => setImmediate(r)); assert.equal(p.calls.filter(c => c[2] === 'PATCH').length, 1); assert.equal(p.requests.length, 0);});
  await test('combined confirmation starts request in tap stack and saves once', async () => {const p = page(); await p.result.save(); p.result.confirmSave(true); assert.equal(p.requests.length, 1); p.result.confirmSave(true); await new Promise(r => setImmediate(r)); assert.equal(p.requests.length, 1); assert.equal(p.calls.filter(c => c[2] === 'PATCH').length, 1); assert.equal(p.calls[0][1].version, 1);});
  await test('attendance validation still prevents invalid completion', async () => {const p = page(); p.result.draft.status = 'completed'; await vue.nextTick(); await p.result.save(); assert(!p.result.savePrompt.value); assert.equal(p.calls.length, 0); assert.equal(p.requests.length, 0); assert(p.result.error.value);});
  const output = path.join(root, 'artifacts/original-notifications-20260915/native-subscription-checks.json');
  fs.writeFileSync(output, JSON.stringify({passed: tested.length, tests: tested, realPermissionSheet: false, realMessages: false}, null, 2));
  console.log(JSON.stringify({passed: tested.length, realPermissionSheet: false, realMessages: false}));
})().catch(error => {console.error(error); process.exitCode = 1;});
