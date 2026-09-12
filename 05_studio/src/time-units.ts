/** UI hours, API integer minutes. Never round an entered fractional minute. */
export function minutesFromHours(value: number | string): number | null {
  const text=String(value).trim();
  if(!/^[+-]?(?:\d+(?:\.\d*)?|\.\d+)$/.test(text))return null;
  const minutes=Number(text)*60,rounded=Math.round(minutes);
  return Number.isSafeInteger(rounded)&&Math.abs(minutes-rounded)<1e-7?rounded:null;
}

/** Retain legacy minute precision when opening and re-saving an existing record. */
export function hoursInput(minutes: number | null | undefined): string {
  return minutes==null?'':String(minutes/60);
}

export function hoursNumber(minutes: number): string {
  return String(Math.round(minutes/60*100)/100);
}
