import {miniSession, studioCall} from './miniapp-client';

type Status = {bound: boolean; admin?: boolean; enabled?: boolean; template_id?: string; nonce?: string};
export type OwnerSubscription = {ticket: string; template: string; nonce: string; expires: number; used: boolean};
export type SubscriptionResult = 'accept' | 'reject' | 'ban' | 'unavailable' | 'failed';

export async function prepareOwnerSubscription(): Promise<OwnerSubscription | null> {
  // Permission itself is never requested during loading. Prepare the identity
  // proof first so the later request can run synchronously inside a real tap.
  // #ifdef MP-WEIXIN
  const started = Date.now();
  const session = await miniSession();
  const status = await studioCall<Status>('/owner-wechat/status', {}, session.ticket, '', 'GET');
  if (!status.bound || !status.admin || !status.enabled || !status.template_id || !status.nonce) return null;
  const expires = started + Math.max(0, Math.min(240, session.expires_in - 30)) * 1000;
  if (Date.now() >= expires) return null;
  return {ticket: session.ticket, template: status.template_id, nonce: status.nonce, expires, used: false};
  // #endif
  // #ifndef MP-WEIXIN
  return null;
  // #endif
}

export function ownerSubscriptionReady(prompt: OwnerSubscription | null): prompt is OwnerSubscription {
  return !!prompt && !prompt.used && Date.now() < prompt.expires;
}

export function requestOwnerSubscription(prompt: OwnerSubscription | null, actionFinished: Promise<unknown> = Promise.resolve()): Promise<SubscriptionResult> {
  if (!ownerSubscriptionReady(prompt)) return Promise.resolve('unavailable');
  prompt.used = true;
  // This Promise executor runs immediately in the confirm button's tap stack.
  // Never await login, save, a modal, or any network request before this call.
  return new Promise(resolve => {
    // #ifdef MP-WEIXIN
    let handled = false;
    try {
      uni.requestSubscribeMessage({
        tmplIds: [prompt.template],
        success: async result => {
          if (handled) return;
          handled = true;
          const choice = (result as unknown as Record<string, string>)[prompt.template];
          if (!['accept', 'reject', 'ban'].includes(choice)) {resolve('failed'); return;}
          // A confirmed booking must finish saving before the grant wakes its
          // waiting notice; otherwise it could consume the next alert itself.
          await actionFinished.catch(() => undefined);
          // Same nonce is safe to retry after an interrupted acknowledgement;
          // the service records one result and never adds a second grant.
          const record = () => studioCall('/owner-wechat/subscribe', {nonce: prompt.nonce, result: choice}, prompt.ticket);
          try {
            try {await record();} catch {await record();}
            resolve(choice as SubscriptionResult);
          } catch {resolve('failed');}
        },
        fail: () => {if (!handled) {handled = true; resolve('failed');}},
      });
    } catch {if (!handled) {handled = true; resolve('failed');}}
    // #endif
    // #ifndef MP-WEIXIN
    resolve('unavailable');
    // #endif
  });
}
