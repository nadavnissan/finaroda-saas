// Stage 7 client-side breadcrumb ring buffer (D-A7). Last 20 events (route changes,
// scan submits, API errors, notification-panel opens), attached to a support ticket so
// admin can debug blind. RED LINE: only safe app metadata is ever recorded here, never a
// journal outcome value (the client does not hold unrevealed values; the server also
// re-sanitizes on write). Pure logic, unit-tested.

export interface Breadcrumb {
  event_type: string; // route_change | scan_submit | api_error | notif_open | ...
  ts: string; // ISO 8601
  path?: string;
  code?: number; // HTTP status for api_error
}

export const MAX_BREADCRUMBS = 20;

/** Append to a fixed-size ring buffer, keeping the newest `max` entries. Pure. */
export function ringPush<T>(list: T[], item: T, max: number): T[] {
  return [...list, item].slice(-max);
}

let buffer: Breadcrumb[] = [];

export function addBreadcrumb(event_type: string, extra?: { path?: string; code?: number }): void {
  buffer = ringPush(buffer, { event_type, ts: new Date().toISOString(), ...extra }, MAX_BREADCRUMBS);
}

/** Oldest-first snapshot (chronological), for the ticket payload / admin timeline. */
export function getBreadcrumbs(): Breadcrumb[] {
  return [...buffer];
}

export function clearBreadcrumbs(): void {
  buffer = [];
}
