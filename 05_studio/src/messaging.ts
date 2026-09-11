import defaults from './content/messaging.json';
import { contentModule } from './content-store';
export const messageCopy = contentModule('messaging', defaults);
export type MessageBridge = {id:string;role:string;sender:string;enabled:boolean;send_enabled:boolean;online:boolean;last_seen:number;health:Record<string,unknown>};
export type MessageThread = {id:string;phone:string;name:string;status:'open'|'closed';unread:number;last_seq:number;enabled:boolean;latest:{content:string;created_at:number;direction:string}|null;reservations:{id:string;status:string;name:string;booking:{date:string;start:string;end:string;guests:number}}[]};
export type CustomerMessage = {seq:number;id:string;thread_id:string;direction:'inbound'|'outbound';source:string;channel:string;content:string;created_at:number;state:string;error:string};
export type ThreadPage = {items:MessageThread[];bridge:MessageBridge|null;next_cursor:string};
export type MessagePage = {thread:MessageThread;items:CustomerMessage[];has_more:boolean;next_before:number|null};
