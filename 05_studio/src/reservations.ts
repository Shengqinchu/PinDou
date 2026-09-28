import { reactive, watch } from "vue";
import { isContentPreview } from './preview-context';
export type ReservationBooking = {
  date: string;
  start: string;
  end: string;
  plan: "hourly" | "day" | "patch" | "";
  guests: number;
};
export type ReservationSlot = {
  start: string;
  end: string;
  available: boolean;
  start_available?: boolean;
  reason: string | null;
  remaining_seats?: number | null;
  capacity_full?: boolean;
  buffered?: boolean;
  low_capacity?: boolean;
};
export type ReservationDay = {
  date: string;
  open: string;
  closed: boolean;
  close: string;
  slots: ReservationSlot[];
};
export type ReservationCalendar = {
  experience?: "beads" | "patch";
  offers?: ReservationOffer[];
  today: string;
  timezone: string;
  minimum_minutes: number;
  max_guests_per_group: number;
  weekly_hours: {
    weekday: number;
    enabled: boolean;
    open: string;
    close: string;
  }[];
  policy_version: number;
  days: ReservationDay[];
};
export type ReservationPayload = {
  contact_profile_version?: number;
  offer?: 'duo4h';
  offer_revision?: string;
  booking: ReservationBooking;
  name: string;
  contact_method: "wechat" | "phone" | "email" | "other";
  contact: string;
  notes: string;
  consent?: boolean; // Compatibility for already-saved requests from older clients.
  locale: "zh" | "en";
  website: string;
};
export type Reservation = {
  creation_source?: 'customer_self' | 'legacy_customer' | 'admin_booking' | 'admin_backfill' | 'unknown';
  can_cancel: boolean;
  offer?: ReservationOffer | null;
  id: string;
  status: string;
  booking: ReservationBooking;
  name: string;
  version: number;
  created_at: string;
  updated_at: string;
  booked_minutes: number;
  actual_minutes: number | null;
  actual_guests: number | null;
  public_note: string;
};
export type ReservationOffer = { id:'duo4h';guests:number;minutes:number;until:string;amount:string;currency:string;label:string[];revision:string };
export function readSession<T>(key: string): T | null {
  if (isContentPreview()) return null;
  try {
    return JSON.parse(sessionStorage.getItem(key) || "null");
  } catch {
    return null;
  }
}
export function saveSession(key: string, value: unknown) {
  if (isContentPreview()) return;
  try {
    if (value === null) sessionStorage.removeItem(key);
    else sessionStorage.setItem(key, JSON.stringify(value));
  } catch {
    /* Session state remains in memory. */
  }
}
const initial: Omit<ReservationPayload, "locale" | "website"> = {
  booking: { date: "", start: "", end: "", plan: "", guests: 1 },
  name: "",
  contact_method: "wechat",
  contact: "",
  notes: "",
};
const saved = readSession<typeof initial>("puppy-reservation-draft-v1");
export const reservationDraft = reactive({
  ...initial,
  ...(saved && typeof saved.name === "string" ? saved : {}),
  booking: { ...initial.booking, ...(saved?.booking || {}) },
});
watch(
  reservationDraft,
  (value) => saveSession("puppy-reservation-draft-v1", value),
  { deep: true },
);
export function minutes(value: string) {
  const [h, m] = value.split(":").map(Number);
  return h * 60 + m;
}
export function clock(value: number) {
  return (
    String(Math.floor(value / 60)).padStart(2, "0") +
    ":" +
    String(value % 60).padStart(2, "0")
  );
}
export function validSelection(
  calendar: ReservationCalendar | null,
  booking: ReservationBooking,
) {
  const day = calendar?.days.find((d) => d.date === booking.date);
  const start = minutes(booking.start),
    end = minutes(booking.end);
  if (
    !day ||
    day.closed ||
    !["hourly", "day", "patch"].includes(booking.plan) ||
    (calendar?.experience || "beads") !== (booking.plan === "patch" ? "patch" : "beads") ||
    !Number.isInteger(booking.guests) ||
    booking.guests < 1 ||
    booking.guests > (calendar?.max_guests_per_group || 4) ||
    !Number.isFinite(start) ||
    !Number.isFinite(end) ||
    (booking.plan === "patch" ? end - start !== 60 : end - start < 120) ||
    start < minutes(day.open || "10:00") ||
    end > minutes(day.close)
  )
    return false;
  if (booking.plan === "day" && booking.end !== day.close) return false;
  const slots = day.slots.filter(
    (s) => minutes(s.start) >= start && minutes(s.start) < end,
  );
  return slots.length === (end - start) / 30 && slots.every((s) => s.available);
}
