import defaults from './content/admin-visits.json';
import { contentModule } from './content-store';
import { say } from './state';
export const adminVisitCopy = contentModule('admin-visits', defaults);
export function visitSourceLabel(source?: string) {
  const keys = ['customer_self', 'legacy_customer', 'admin_booking', 'admin_backfill', 'unknown'] as const;
  const key = keys.find(value => value === source) || 'unknown';
  return say(adminVisitCopy[key]);
}
export function visitStatusLabel(status: string) {
  return say((adminVisitCopy as Record<string, string[]>)[status] || [status, status]);
}
