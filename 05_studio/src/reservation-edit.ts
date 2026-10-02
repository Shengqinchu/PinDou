import defaults from './content/reservation-edit.json';
import { contentModule } from './content-store';
export const reservationEditCopy = contentModule('reservation-edit', defaults);
export function changeRequestKey() {
  return globalThis.crypto?.randomUUID?.() || 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g,c=>{const n=Math.floor(Math.random()*16);return(c==='x'?n:(n&3)|8).toString(16);});
}
