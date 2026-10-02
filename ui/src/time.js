// Sim clock: t is minutes since episode start. Episode starts Wednesday 14:00, so the
// materials line up (Friday build at t=2640 -> Fri 10:00; moved to t=2880 -> Fri 14:00).
export const T0_DAY = 3; // 0=Sun .. 3=Wed
export const T0_MIN = 14 * 60;
const DAYS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];

export function clock(t) {
  const abs = T0_MIN + t;
  const day = DAYS[(T0_DAY + Math.floor(abs / 1440) + 7 * 100) % 7];
  const m = ((abs % 1440) + 1440) % 1440;
  return `${day} ${String(Math.floor(m / 60)).padStart(2, "0")}:${String(m % 60).padStart(2, "0")}`;
}

// day offset (0 = start day) and minute-of-day for calendar placement
export function dayAndMinute(t) {
  const abs = T0_MIN + t;
  return { day: Math.floor(abs / 1440), minute: ((abs % 1440) + 1440) % 1440 };
}

export function dayName(offset) {
  return DAYS[(T0_DAY + offset + 700) % 7];
}

export function ago(tNow, t) {
  const d = tNow - t;
  if (d < 1) return "now";
  if (d < 60) return `${d}m ago`;
  if (d < 1440) return `${Math.floor(d / 60)}h ago`;
  return `${Math.floor(d / 1440)}d ago`;
}
