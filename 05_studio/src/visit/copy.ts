import { contentModule,contentValues } from '../content-store';
import flow from '../content/visit-flow.json';
import visit from '../content/pages-Visit.json';
import rates from '../content/experience-rates.json';
import { say,formatCopy } from '../state';
export const copy=contentModule('visit-flow',flow);
export const words=contentModule('pages-Visit',visit);
export const prices=contentValues('rate-fields',rates);
export const guestCount=(count:number)=>count===1?say(copy.single_guest):formatCopy(copy.guest_count,{v0:count});
