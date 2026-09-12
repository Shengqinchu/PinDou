import accountCopy from './content/account.json';
// Legacy provider placeholders are protocol values, not display copy.
const defaults=[...accountCopy.default_name,'\u5fae\u4fe1\u7528\u6237','WeChat user'];
export function defaultDisplayName(value: string | null | undefined): boolean {
  const name=value?.trim()||'';
  return !name||defaults.some(label=>name===label||(name.startsWith(label)&&/^[ _#-][A-Fa-f0-9]+$/.test(name.slice(label.length))));
}
export function needsProfileSetup(profile: {nickname?: string;avatar?: string}, booking?: {complete?:boolean}): boolean {
  return defaultDisplayName(profile.nickname)||!profile.avatar||!booking?.complete;
}
export function validWechatId(value:string):boolean {
  return !value.trim()||/^[A-Za-z0-9_.-]{3,80}$/.test(value.trim());
}
