import { ref } from 'vue';
import { contentModule } from './content-store';
import words from './content/reservation-cancellation.json';
import { say } from './state';
export const cancellationCopy=contentModule('reservation-cancellation',words);
export const reservationRevision=ref(0);
export type CancellationPolicy={limit:number;used:number;remaining:number;reset_date:string;month:string;timezone:string;eligible:boolean;reason:'reservation_cancellation_limit'|'reservation_cancellation_unavailable'|null;version:number};
export function reservationStatus(status:string){return say(cancellationCopy[status as 'pending'|'confirmed'|'completed'|'cancelled']||cancellationCopy.pending);}
